import importlib.metadata as metadata
import os
import sys
import types

import pytest
from fastapi.testclient import TestClient

try:
    metadata.version("mem0ai")
except metadata.PackageNotFoundError:  # type: ignore[attr-defined]
    _orig_version = metadata.version

    def _patched_version(name: str) -> str:
        if name == "mem0ai":
            return "0.0.0-test"
        return _orig_version(name)

    metadata.version = _patched_version  # type: ignore[assignment]

os.environ.setdefault("HISTORY_DB_PATH", "./.test-history.db")


class DummyMemory:
    def __init__(self):
        self.next_id = 1
        self.storage = {}

    def add(self, messages, **params):
        memory_id = f"mem-{self.next_id}"
        self.next_id += 1
        record = {
            "id": memory_id,
            "memory": messages[0]["content"] if messages else "",
            "user_id": params.get("user_id"),
        }
        record.update(params)
        self.storage[memory_id] = record
        return {"memory_id": memory_id, "user_id": record["user_id"]}

    def get_all(self, **params):
        results = [record for record in self.storage.values() if self._match(record, params)]
        return {"results": results}

    def get(self, memory_id):
        return self.storage.get(memory_id)

    def search(self, query, **params):
        results = [record for record in self.storage.values() if self._match(record, params)]
        return {"results": results}

    def update(self, memory_id, data):
        record = self.storage[memory_id]
        record["memory"] = data
        return record

    def history(self, memory_id):
        return [self.storage[memory_id]]

    def delete(self, memory_id):
        self.storage.pop(memory_id, None)

    def delete_all(self, **params):
        for key in list(self.storage.keys()):
            if self._match(self.storage[key], params):
                self.storage.pop(key)

    def reset(self):
        self.storage.clear()

    @staticmethod
    def _match(record, params):
        return all(record.get(k) == v for k, v in params.items())


class _MemoryStub:
    @classmethod
    def from_config(cls, config):
        return DummyMemory()


if "mem0" not in sys.modules:
    stub = types.ModuleType("mem0")
    stub.Memory = _MemoryStub
    stub.AsyncMemory = _MemoryStub
    sys.modules["mem0"] = stub

import server.main as main
from server.auth import AuthError, Identity


class DummyVerifier:
    def verify_authorization_header(self, authorization: str) -> Identity:
        if not authorization:
            raise AuthError(401, "AUTH_HEADER_MISSING", "Authorization header missing.")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise AuthError(401, "AUTH_TOKEN_MISSING", "Authorization header is malformed.")
        sub, _, scope_part = token.partition(":")
        scopes = set(filter(None, scope_part.split(","))) if scope_part else set()
        claims = {"sub": sub, "scope": " ".join(sorted(scopes))}
        return Identity(sub=sub, scopes=scopes, claims=claims, token=token, jwks_cache_hit=True)


@pytest.fixture
def client(monkeypatch):
    dummy_memory = DummyMemory()
    dummy_verifier = DummyVerifier()

    monkeypatch.setattr(main, "JWT_VERIFIER", dummy_verifier)
    monkeypatch.setattr(main, "init_memory", lambda: None)
    monkeypatch.setattr(main, "MEMORY_INSTANCE", dummy_memory)
    monkeypatch.setattr(main, "MEMORY_INIT_ERROR", None)
    monkeypatch.setattr(main, "get_memory_instance", lambda: dummy_memory)

    return TestClient(main.app), dummy_memory


def _auth_header(sub: str, *scopes: str) -> dict:
    scope_str = ",".join(scopes)
    token = f"{sub}:{scope_str}" if scope_str else sub
    return {"Authorization": f"Bearer {token}"}


def test_add_memory_defaults_to_sub(client):
    api, memory = client
    payload = {"messages": [{"role": "user", "content": "hello"}]}
    resp = api.post("/memories", json=payload, headers=_auth_header("user-1", main.READ_SCOPE, main.WRITE_SCOPE))
    assert resp.status_code == 200
    created = resp.json()
    stored = memory.get(created["memory_id"])  # type: ignore[index]
    assert stored["user_id"] == "user-1"


def test_add_memory_cross_user_requires_admin(client):
    api, _ = client
    payload = {"messages": [{"role": "user", "content": "hi"}], "user_id": "other"}
    resp = api.post("/memories", json=payload, headers=_auth_header("user-1", main.READ_SCOPE, main.WRITE_SCOPE))
    assert resp.status_code == 403
    body = resp.json()
    assert body["error"]["code"] == "FORBIDDEN"
    assert body["error"]["details"]["requested_user_id"] == "other"


def test_admin_can_override_user(client):
    api, memory = client
    payload = {"messages": [{"role": "user", "content": "hi"}], "user_id": "other"}
    resp = api.post(
        "/memories",
        json=payload,
        headers=_auth_header("admin", main.READ_SCOPE, main.WRITE_SCOPE, main.ADMIN_SCOPE),
    )
    assert resp.status_code == 200
    created = resp.json()
    stored = memory.get(created["memory_id"])  # type: ignore[index]
    assert stored["user_id"] == "other"


def test_read_requires_scope(client):
    api, _ = client
    resp = api.get("/memories", params={"user_id": "user-1"}, headers=_auth_header("user-1", main.WRITE_SCOPE))
    assert resp.status_code == 403
    body = resp.json()
    assert body["error"]["details"]["required_scope"] == main.READ_SCOPE


def test_update_requires_write_scope(client):
    api, memory = client
    record = memory.add([{"role": "user", "content": "hello"}], user_id="user-1")
    memory_id = record["memory_id"]

    resp = api.put(
        f"/memories/{memory_id}",
        json={"memory": "updated"},
        headers=_auth_header("user-1", main.READ_SCOPE),
    )
    assert resp.status_code == 403
    body = resp.json()
    assert body["error"]["details"]["required_scope"] == main.WRITE_SCOPE

    resp_ok = api.put(
        f"/memories/{memory_id}",
        json={"memory": "updated"},
        headers=_auth_header("user-1", main.READ_SCOPE, main.WRITE_SCOPE),
    )
    assert resp_ok.status_code == 200
    assert memory.get(memory_id)["memory"] == "updated"


def test_update_cross_user_requires_admin(client):
    api, memory = client
    record = memory.add([{"role": "user", "content": "hi"}], user_id="someone-else")
    memory_id = record["memory_id"]

    resp = api.put(
        f"/memories/{memory_id}",
        json={"memory": "updated"},
        headers=_auth_header("user-1", main.READ_SCOPE, main.WRITE_SCOPE),
    )
    assert resp.status_code == 403

    resp_admin = api.put(
        f"/memories/{memory_id}",
        json={"memory": "admin update"},
        headers=_auth_header("admin", main.READ_SCOPE, main.WRITE_SCOPE, main.ADMIN_SCOPE),
    )
    assert resp_admin.status_code == 200
    assert memory.get(memory_id)["memory"] == "admin update"


def test_config_requires_admin_and_write(client):
    api, _ = client
    config = {"vector_store": {"provider": "mock", "config": {"collection_name": "demo"}}}
    resp = api.post("/configure", json=config, headers=_auth_header("user-1", main.WRITE_SCOPE))
    assert resp.status_code == 403

    resp_admin = api.post(
        "/configure",
        json=config,
        headers=_auth_header("admin", main.WRITE_SCOPE, main.ADMIN_SCOPE),
    )
    assert resp_admin.status_code == 200


def test_reset_requires_admin(client):
    api, memory = client
    memory.add([{"role": "user", "content": "hi"}], user_id="user-1")
    resp = api.post("/reset", headers=_auth_header("user-1", main.READ_SCOPE, main.WRITE_SCOPE))
    assert resp.status_code == 403

    resp_admin = api.post(
        "/reset",
        headers=_auth_header("admin", main.READ_SCOPE, main.WRITE_SCOPE, main.ADMIN_SCOPE),
    )
    assert resp_admin.status_code == 200
    assert memory.storage == {}


def test_health_endpoint(client):
    api, _ = client
    resp = api.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
