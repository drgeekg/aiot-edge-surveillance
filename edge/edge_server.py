from contextlib import asynccontextmanager
import os
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from edge import controller as edge_controller
from server.app import (
    ALLOWED_CORS_ORIGINS,
    EdgeConfigUpdate,
    install_proactor_silence_handler,
    verify_api_key,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the standalone edge emitter loop on startup and stop cleanly on exit."""
    install_proactor_silence_handler()
    target = os.getenv("AIIOT_SERVER_URL", "http://127.0.0.1:8000").rstrip("/")
    edge_controller.controller.server_url = target
    edge_controller.controller.start()
    try:
        yield
    finally:
        edge_controller.controller.stop()


app = FastAPI(title="Edge Node Control & Emitter API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def get_health():
    return {
        "status": "ok",
        "role": "edge-node",
        "target_server": edge_controller.controller.server_url,
        "streaming": edge_controller.controller.cfg.get("streaming", True),
    }


@app.get("/edge/status")
def get_edge_status():
    return edge_controller.controller.get_status()


@app.post("/edge/config", dependencies=[Depends(verify_api_key)])
def post_edge_config(payload: EdgeConfigUpdate, request: Request = None):
    verify_api_key(request)
    try:
        return edge_controller.controller.update_config(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/edge/frame")
def get_edge_frame():
    jpeg = edge_controller.controller.latest_jpeg
    if not jpeg:
        raise HTTPException(status_code=404, detail="No edge frame captured yet")
    return Response(content=jpeg, media_type="image/jpeg")
