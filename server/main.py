import logging
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from fastapi.exceptions import RequestValidationError

from mem0 import Memory
from server.auth import AuthError, Identity, JWTVerifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Load environment variables
load_dotenv()


POSTGRES_HOST = os.environ.get("POSTGRES_HOST")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
POSTGRES_DB = os.environ.get("POSTGRES_DB")
POSTGRES_USER = os.environ.get("POSTGRES_USER")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD")
POSTGRES_COLLECTION_NAME = os.environ.get("POSTGRES_COLLECTION_NAME", "memories")

NEO4J_URI = os.environ.get("NEO4J_URI")
NEO4J_USERNAME = os.environ.get("NEO4J_USERNAME")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")

MEMGRAPH_URI = os.environ.get("MEMGRAPH_URI")
MEMGRAPH_USERNAME = os.environ.get("MEMGRAPH_USERNAME")
MEMGRAPH_PASSWORD = os.environ.get("MEMGRAPH_PASSWORD")

AUTH0_DOMAIN = os.environ.get("AUTH0_DOMAIN")
AUTH0_AUDIENCE = os.environ.get("AUTH0_AUDIENCE")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
MEM0_ALLOW_RUNTIME_CONFIG = os.environ.get("MEM0_ALLOW_RUNTIME_CONFIG", "").lower() in {"1", "true", "yes"}
HISTORY_DB_PATH = os.environ.get("HISTORY_DB_PATH", "/app/history/history.db")
ENABLE_GRAPH = os.environ.get("MEM0_ENABLE_GRAPH", "").lower() in {"1", "true", "yes"}

RATE_LIMIT_PER_MINUTE = int(os.environ.get("MEM0_RATE_LIMIT_PER_MINUTE", "0") or 0)
_rate_windows = {}

JWT_VERIFIER: Optional[JWTVerifier] = None
if AUTH0_DOMAIN and AUTH0_AUDIENCE:
    try:
        JWT_VERIFIER = JWTVerifier(AUTH0_DOMAIN, AUTH0_AUDIENCE)
    except ValueError as exc:
        logging.error("Invalid Auth0 configuration: %s", exc)
else:
    logging.warning("Auth0 domain or audience not configured; protected endpoints will reject requests until configured.")


def json_error(code: str, message: str, details: dict | None = None) -> dict:
    err = {"error": {"code": code, "message": message}}
    if details:
        err["error"]["details"] = details
    return err

def require_identity(authorization: str = Header(default=None)) -> Identity:
    if JWT_VERIFIER is None:
        raise HTTPException(
            status_code=503,
            detail=json_error("AUTH_NOT_CONFIGURED", "Auth0 configuration is not ready."),
        )
    try:
        identity = JWT_VERIFIER.verify_authorization_header(authorization)
    except AuthError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=json_error(exc.code, exc.message, exc.details),
        )
    return identity

ADMIN_SCOPE = "mem0:admin"
READ_SCOPE = "mem0:read"
WRITE_SCOPE = "mem0:write"


def has_admin(identity: Identity) -> bool:
    return ADMIN_SCOPE in identity.scopes


def has_scope(identity: Identity, scope: str) -> bool:
    return scope in identity.scopes


def require_scope(
    identity: Identity,
    scope: str,
    *,
    operation: str,
    resource: Optional[str] = None,
) -> None:
    if has_admin(identity) or has_scope(identity, scope):
        return
    details = {"required_scope": scope, "sub": identity.sub, "operation": operation}
    if resource is not None:
        details["resource"] = resource
    raise HTTPException(
        status_code=403,
        detail=json_error("FORBIDDEN", f"Scope {scope} is required for this operation.", details),
    )


def require_scopes(
    identity: Identity,
    scopes: List[str],
    *,
    operation: str,
    resource: Optional[str] = None,
) -> None:
    for scope in scopes:
        require_scope(identity, scope, operation=operation, resource=resource)


def bind_user_to_identity(
    requested_user_id: Optional[str],
    identity: Identity,
    *,
    operation: str,
    resource: Optional[str] = None,
) -> str:
    if requested_user_id is None:
        return identity.sub
    if requested_user_id == identity.sub or has_admin(identity):
        return requested_user_id
    details = {
        "requested_user_id": requested_user_id,
        "sub": identity.sub,
        "operation": operation,
    }
    if resource is not None:
        details["resource"] = resource
    raise HTTPException(
        status_code=403,
        detail=json_error("FORBIDDEN", "Cross-user access requires mem0:admin", details),
    )


def ensure_memory_access(
    record: Dict[str, Any],
    identity: Identity,
    *,
    operation: str,
    resource: str,
) -> None:
    owner = record.get("user_id")
    if owner is None:
        if has_admin(identity):
            return
        raise HTTPException(
            status_code=403,
            detail=json_error(
                "FORBIDDEN",
                "Memory ownership is undefined; admin token required.",
                {"operation": operation, "resource": resource, "sub": identity.sub},
            ),
        )
    if owner == identity.sub or has_admin(identity):
        return
    raise HTTPException(
        status_code=403,
        detail=json_error(
            "FORBIDDEN",
            "Cross-user access requires mem0:admin",
            {"owner": owner, "sub": identity.sub, "operation": operation, "resource": resource},
        ),
    )


history_dir = os.path.dirname(HISTORY_DB_PATH)
if history_dir:
    os.makedirs(history_dir, exist_ok=True)

vector_store_config: Optional[Dict[str, Any]] = None
if all([POSTGRES_HOST, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD]):
    vector_store_config = {
        "provider": "pgvector",
        "config": {
            "host": POSTGRES_HOST,
            "port": int(POSTGRES_PORT),
            "dbname": POSTGRES_DB,
            "user": POSTGRES_USER,
            "password": POSTGRES_PASSWORD,
            "collection_name": POSTGRES_COLLECTION_NAME,
        },
    }
else:
    logging.error(
        "Postgres configuration is incomplete. Set POSTGRES_HOST, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD."
    )

graph_store_config: Optional[Dict[str, Any]] = None
if ENABLE_GRAPH:
    if all([NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD]):
        graph_store_config = {
            "provider": "neo4j",
            "config": {"url": NEO4J_URI, "username": NEO4J_USERNAME, "password": NEO4J_PASSWORD},
        }
    else:
        logging.warning(
            "MEM0_ENABLE_GRAPH is set but Neo4j credentials are missing. Graph features will remain disabled."
        )

DEFAULT_CONFIG = {
    "version": "v1.1",
    "llm": {"provider": "openai", "config": {"api_key": OPENAI_API_KEY, "temperature": 0.2, "model": "gpt-4o"}},
    "embedder": {"provider": "openai", "config": {"api_key": OPENAI_API_KEY, "model": "text-embedding-3-small"}},
    "history_db_path": HISTORY_DB_PATH,
}

if vector_store_config:
    DEFAULT_CONFIG["vector_store"] = vector_store_config

if graph_store_config:
    DEFAULT_CONFIG["graph_store"] = graph_store_config

MEMORY_INSTANCE: Optional[Memory] = None
MEMORY_INIT_ERROR: Optional[str] = None


def init_memory():
    """Initialise the Mem0 backend, capturing any errors instead of crashing the process."""
    global MEMORY_INSTANCE, MEMORY_INIT_ERROR
    if MEMORY_INSTANCE is not None:
        return
    try:
        if not vector_store_config:
            raise RuntimeError(
                "Vector store not configured. Provide Postgres + pgvector credentials via environment variables."
            )
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is required to run the Mem0 server.")
        MEMORY_INSTANCE = Memory.from_config(DEFAULT_CONFIG)
        MEMORY_INIT_ERROR = None
    except Exception as exc:
        MEMORY_INSTANCE = None
        MEMORY_INIT_ERROR = str(exc)
        logging.exception("Failed to initialise Mem0 backend.")


def get_memory_instance() -> Memory:
    """Return the initialised Memory instance or raise if unavailable."""
    init_memory()
    if MEMORY_INSTANCE is None:
        message = MEMORY_INIT_ERROR or "Mem0 backend not ready."
        raise HTTPException(status_code=503, detail=message)
    return MEMORY_INSTANCE


app = FastAPI(
    title="Mem0 REST APIs",
    description="A REST API for managing and searching memories for your AI Agents and Apps.",
    version="1.0.0",
)

@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if RATE_LIMIT_PER_MINUTE <= 0:
        return await call_next(request)
    path = request.url.path
    if path in {"/health", "/docs", "/openapi.json"}:
        return await call_next(request)
    # naive per-IP per-minute window
    ip = request.client.host if request.client else "unknown"
    key = (ip, path)
    import time
    now = int(time.time())
    window = now // 60
    count, curwin = _rate_windows.get(key, (0, window))
    if curwin != window:
        count = 0
        curwin = window
    count += 1
    _rate_windows[key] = (count, curwin)
    if count > RATE_LIMIT_PER_MINUTE:
        from fastapi import status
        return JSONResponse(json_error("RATE_LIMIT_EXCEEDED", "Too many requests.", {"limit": RATE_LIMIT_PER_MINUTE, "window": "1m"}), status_code=status.HTTP_429_TOO_MANY_REQUESTS, headers={"Retry-After": "60"})
    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(json_error("VALIDATION_ERROR", "Invalid request.", {"errors": exc.errors()}), status_code=422)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "error" in detail:
        payload = detail
    else:
        payload = json_error("HTTP_ERROR", str(detail))
    return JSONResponse(payload, status_code=exc.status_code)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    import traceback
    import logging as _logging
    _logging.exception("Unhandled error: %s", exc)
    return JSONResponse(json_error("INTERNAL_ERROR", "An unexpected error occurred."), status_code=500)

class Message(BaseModel):
    role: str = Field(..., description="Role of the message (user or assistant).")
    content: str = Field(..., description="Message content.")


class MemoryCreate(BaseModel):
    messages: List[Message] = Field(..., description="List of messages to store.")
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    run_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query.")
    user_id: Optional[str] = None
    run_id: Optional[str] = None
    agent_id: Optional[str] = None
    limit: Optional[int] = Field(default=None, description="Max results to return.")
    summary: Optional[bool] = Field(default=False, description="Return a compact summary of results.")
    max_summary_tokens: Optional[int] = Field(default=150, description="Upper bound for summary tokens.")
    filters: Optional[Dict[str, Any]] = None


@app.post("/configure", summary="Configure Mem0")
def set_config(config: Dict[str, Any], identity: Identity = Depends(require_identity)):
    """Set memory configuration."""
    if not MEM0_ALLOW_RUNTIME_CONFIG:
        raise HTTPException(
            status_code=403,
            detail=json_error("FORBIDDEN", "Runtime configuration is disabled.", {"operation": "config:set"}),
        )
    if not has_admin(identity):
        raise HTTPException(
            status_code=403,
            detail=json_error(
                "FORBIDDEN",
                "Admin scope mem0:admin is required to update configuration.",
                {"operation": "config:set", "sub": identity.sub},
            ),
        )
    require_scope(identity, WRITE_SCOPE, operation="config:set")
    global MEMORY_INSTANCE, MEMORY_INIT_ERROR, DEFAULT_CONFIG
    MEMORY_INSTANCE = Memory.from_config(config)
    DEFAULT_CONFIG = config
    MEMORY_INIT_ERROR = None
    return {"message": "Configuration set successfully"}


@app.post("/memories", summary="Create memories")
def add_memory(memory_create: MemoryCreate, identity: Identity = Depends(require_identity)):
    """Store new memories."""
    require_scope(identity, WRITE_SCOPE, operation="memories:create")
    bound_user_id = bind_user_to_identity(
        memory_create.user_id, identity, operation="memories:create", resource="payload"
    )
    memory_create.user_id = bound_user_id

    params = {k: v for k, v in memory_create.model_dump().items() if v is not None and k != "messages"}
    params["user_id"] = bound_user_id
    try:
        memory = get_memory_instance()
        response = memory.add(messages=[m.model_dump() for m in memory_create.messages], **params)
        return JSONResponse(content=response)
    except Exception as e:
        logging.exception("Error in add_memory:")  # This will log the full traceback
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memories", summary="Get memories")
def get_all_memories(
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    identity: Identity = Depends(require_identity),
):
    """Retrieve stored memories."""
    require_scope(identity, READ_SCOPE, operation="memories:list")
    user_id = bind_user_to_identity(user_id, identity, operation="memories:list", resource="query")
    try:
        memory = get_memory_instance()
        params = {
            k: v for k, v in {"user_id": user_id, "run_id": run_id, "agent_id": agent_id}.items() if v is not None
        }
        return memory.get_all(**params)
    except Exception as e:
        logging.exception("Error in get_all_memories:")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memories/{memory_id}", summary="Get a memory")
def get_memory_item(memory_id: str, identity: Identity = Depends(require_identity)):
    """Retrieve a specific memory by ID."""
    require_scope(identity, READ_SCOPE, operation="memories:get", resource=memory_id)
    try:
        memory = get_memory_instance()
        record = memory.get(memory_id)
        if record is None:
            raise HTTPException(
                status_code=404,
                detail=json_error("NOT_FOUND", "Memory not found.", {"memory_id": memory_id}),
            )
        ensure_memory_access(record, identity, operation="memories:get", resource=memory_id)
        return record
    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Error in get_memory:")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search", summary="Search memories")
def search_memories(search_req: SearchRequest, identity: Identity = Depends(require_identity)):
    """Search for memories based on a query."""
    require_scope(identity, READ_SCOPE, operation="memories:search")
    try:
        memory = get_memory_instance()
        payload = search_req.model_dump()
        payload["user_id"] = bind_user_to_identity(
            payload.get("user_id"), identity, operation="memories:search", resource="query"
        )
        summary = payload.pop("summary", False)
        max_summary_tokens = payload.pop("max_summary_tokens", 150)
        query = payload.pop("query")
        results = memory.search(query=query, **{k: v for k, v in payload.items() if v is not None})
        if summary:
            try:
                mem_texts = [r.get("memory", "") for r in results.get("results", []) if r.get("memory")]
                if mem_texts:
                    content = "\n".join(f"- {m}" for m in mem_texts)
                    system = "You are a concise assistant. Summarize the following memories in <=150 tokens without bullets. Focus on stable preferences and facts."
                    msg = [{"role": "system", "content": system}, {"role": "user", "content": content}]
                    summary_text = memory.llm.generate_response(msg, max_tokens=max_summary_tokens)
                    if isinstance(summary_text, dict) and "content" in summary_text:
                        summary_text = summary_text.get("content")
                    results["summary"] = summary_text
                else:
                    results["summary"] = ""
            except Exception as se:
                logging.exception("Error generating summary: %s", se)
                results["summary"] = ""
        return JSONResponse(content=results)
    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Error in search_memories:")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/memories/{memory_id}", summary="Update a memory")
def update_memory(memory_id: str, updated_memory: Dict[str, Any], identity: Identity = Depends(require_identity)):
    """Update an existing memory with new content."""
    require_scopes(identity, [READ_SCOPE, WRITE_SCOPE], operation="memories:update", resource=memory_id)
    try:
        memory = get_memory_instance()
        record = memory.get(memory_id)
        if record is None:
            raise HTTPException(
                status_code=404,
                detail=json_error("NOT_FOUND", "Memory not found.", {"memory_id": memory_id}),
            )
        ensure_memory_access(record, identity, operation="memories:update", resource=memory_id)

        update_text = None
        if isinstance(updated_memory, dict):
            update_text = (
                updated_memory.get("data")
                or updated_memory.get("memory")
            )
            if update_text is None:
                messages = updated_memory.get("messages")
                if isinstance(messages, list) and messages:
                    first = messages[0]
                    if isinstance(first, dict):
                        update_text = first.get("content")
        else:
            update_text = str(updated_memory)

        if not update_text:
            raise HTTPException(
                status_code=400,
                detail=json_error("UPDATE_PAYLOAD_INVALID", "Provide updated text via 'data', 'memory', or 'messages'."),
            )

        return memory.update(memory_id=memory_id, data=update_text)
    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Error in update_memory:")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memories/{memory_id}/history", summary="Get memory history")
def memory_history(memory_id: str, identity: Identity = Depends(require_identity)):
    """Retrieve memory history."""
    require_scope(identity, READ_SCOPE, operation="memories:history", resource=memory_id)
    try:
        memory = get_memory_instance()
        record = memory.get(memory_id)
        if record is None:
            raise HTTPException(
                status_code=404,
                detail=json_error("NOT_FOUND", "Memory not found.", {"memory_id": memory_id}),
            )
        ensure_memory_access(record, identity, operation="memories:history", resource=memory_id)
        return memory.history(memory_id=memory_id)
    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Error in memory_history:")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/memories/{memory_id}", summary="Delete a memory")
def delete_memory(memory_id: str, identity: Identity = Depends(require_identity)):
    """Delete a specific memory by ID."""
    require_scopes(identity, [READ_SCOPE, WRITE_SCOPE], operation="memories:delete", resource=memory_id)
    try:
        memory = get_memory_instance()
        record = memory.get(memory_id)
        if record is None:
            raise HTTPException(
                status_code=404,
                detail=json_error("NOT_FOUND", "Memory not found.", {"memory_id": memory_id}),
            )
        ensure_memory_access(record, identity, operation="memories:delete", resource=memory_id)
        memory.delete(memory_id=memory_id)
        return {"message": "Memory deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Error in delete_memory:")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/memories", summary="Delete all memories")
def delete_all_memories(
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    identity: Identity = Depends(require_identity),
):
    """Delete all memories for a given identifier."""
    require_scope(identity, WRITE_SCOPE, operation="memories:delete_all")
    user_id = bind_user_to_identity(user_id, identity, operation="memories:delete_all", resource="query")
    try:
        memory = get_memory_instance()
        params = {
            k: v for k, v in {"user_id": user_id, "run_id": run_id, "agent_id": agent_id}.items() if v is not None
        }
        memory.delete_all(**params)
        return {"message": "All relevant memories deleted"}
    except Exception as e:
        logging.exception("Error in delete_all_memories:")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reset", summary="Reset all memories")
def reset_memory(identity: Identity = Depends(require_identity)):
    """Completely reset stored memories."""
    require_scope(identity, WRITE_SCOPE, operation="memories:reset")
    if not has_admin(identity):
        raise HTTPException(
            status_code=403,
            detail=json_error("FORBIDDEN", "Admin scope mem0:admin is required to reset all memories.", {"operation": "memories:reset", "sub": identity.sub}),
        )
    try:
        memory = get_memory_instance()
        memory.reset()
        return {"message": "All memories reset"}
    except Exception as e:
        logging.exception("Error in reset_memory:")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/whoami", summary="Report request identity")
def whoami(identity: Identity = Depends(require_identity)):
    """Return the authenticated caller plus raw claims for debugging."""
    return {
        "status": "ok",
        "sub": identity.sub,
        "scopes": sorted(identity.scopes),
        "claims": identity.claims,
        "jwks_cache_hit": identity.jwks_cache_hit,
    }


@app.get("/", summary="Redirect to the OpenAPI documentation", include_in_schema=False)
def home():
    """Redirect to the OpenAPI documentation."""
    return RedirectResponse(url="/docs")


@app.get("/health", summary="Health check", include_in_schema=False)
def health():
    """Return readiness status of the memory backend."""
    if MEMORY_INSTANCE is None:
        init_memory()
    if MEMORY_INSTANCE is None:
        raise HTTPException(
            status_code=503,
            detail={"status": "error", "message": MEMORY_INIT_ERROR or "Mem0 backend not ready."},
        )
    return {"status": "ok"}


@app.on_event("startup")
def startup_event():
    """Attempt to initialise the memory backend during startup."""
    init_memory()
