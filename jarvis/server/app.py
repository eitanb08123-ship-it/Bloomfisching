import asyncio
import json
import os
from pathlib import Path

import psutil
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from jarvis.core.ai_core import AICore
from jarvis.core.undo_stack import UndoStack
from jarvis.memory.memory_store import MemoryStore
from jarvis.permissions.manager import PermissionManager
from jarvis.tools.registry import ToolRegistry
from jarvis.utils.config import load_settings
from jarvis.utils.logger import get_logger
from jarvis.voice import speech_input, speech_output

log = get_logger("server")

STATIC_DIR = Path(__file__).resolve().parent / "static"

settings = load_settings()
memory_store = MemoryStore(max_history_messages=settings["memory"]["max_history_messages"])
undo_stack = UndoStack()
tool_registry = ToolRegistry(settings, memory_store, undo_stack)

_active_socket: WebSocket | None = None


async def _request_confirmation(request_id: str, tool, args: dict, stage: int) -> None:
    if _active_socket is None:
        return
    await _active_socket.send_json(
        {
            "type": "confirmation_request",
            "request_id": request_id,
            "tool": tool.name,
            "description": tool.description,
            "tier": tool.tier.value,
            "stage": stage,
            "args": args,
        }
    )


async def _report_activity(tool_name: str, args: dict, result: str) -> None:
    if _active_socket is None:
        return
    await _active_socket.send_json({"type": "activity", "tool": tool_name, "args": args, "result": result})


_autonomous = settings["permissions"].get("mode", "confirm") == "autonomous"
if _autonomous:
    log.warning("Permissions mode is 'autonomous': tools run with no confirmation, undo is the only safety net.")
permission_manager = PermissionManager(_request_confirmation, autonomous=_autonomous)
ai_core = AICore(settings, memory_store, tool_registry, permission_manager, on_activity=_report_activity)

app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global _active_socket
    await websocket.accept()
    _active_socket = websocket
    log.info("UI connected")

    provider_labels = {"AnthropicProvider": "ANTHROPIC", "GroqProvider": "GROQ"}
    mode = provider_labels.get(ai_core.provider.__class__.__name__, "ECHO")
    await websocket.send_json({"type": "mode", "mode": mode})

    for message in memory_store.get_history():
        role_type = "assistant_message" if message["role"] == "assistant" else "user_message"
        await websocket.send_json({"type": role_type, "text": message["content"], "history": True})

    status_task = asyncio.create_task(_status_loop(websocket))
    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            await _handle_client_message(websocket, data)
    except WebSocketDisconnect:
        log.info("UI disconnected")
    finally:
        status_task.cancel()
        if _active_socket is websocket:
            _active_socket = None


async def _handle_client_message(websocket: WebSocket, data: dict) -> None:
    msg_type = data.get("type")

    # user_message/voice_listen must run as background tasks, not be awaited here:
    # handling one can block on a confirmation, and awaiting it would stop this
    # loop from ever reading the confirm_response that would unblock it.
    if msg_type == "user_message":
        asyncio.create_task(_process_user_text(websocket, data["text"]))
    elif msg_type == "confirm_response":
        permission_manager.resolve(data["request_id"], bool(data["approved"]))
    elif msg_type == "clear_history":
        memory_store.clear_history()
        await websocket.send_json({"type": "assistant_message", "text": "History cleared."})
    elif msg_type == "voice_listen":
        asyncio.create_task(_handle_voice_listen(websocket))
    else:
        log.warning("Unknown message type from client: %s", msg_type)


async def _process_user_text(websocket: WebSocket, text: str) -> None:
    await websocket.send_json({"type": "thinking", "value": True})
    try:
        reply = await ai_core.handle_message(text)
    except Exception as exc:  # keep the UI alive even if something unexpected breaks
        log.exception("Error handling message")
        reply = f"Internal error: {exc}"
    await websocket.send_json({"type": "thinking", "value": False})
    await websocket.send_json({"type": "assistant_message", "text": reply})

    if settings["voice"]["enabled"] and speech_output.is_available():
        await asyncio.to_thread(speech_output.speak, reply, settings["voice"]["tts_rate"])


async def _handle_voice_listen(websocket: WebSocket) -> None:
    if not speech_input.is_available():
        await websocket.send_json(
            {"type": "error", "message": "Voice input isn't installed (SpeechRecognition/PyAudio)."}
        )
        return

    await websocket.send_json({"type": "listening", "value": True})
    try:
        text = await asyncio.to_thread(speech_input.listen_once, settings["voice"]["input_language"])
    except RuntimeError as exc:
        await websocket.send_json({"type": "listening", "value": False})
        await websocket.send_json({"type": "error", "message": str(exc)})
        return

    await websocket.send_json({"type": "listening", "value": False})
    await websocket.send_json({"type": "voice_transcript", "text": text})
    await _process_user_text(websocket, text)


async def _status_loop(websocket: WebSocket) -> None:
    disk_root = os.path.abspath(os.sep)
    try:
        while True:
            status = {
                "type": "status_update",
                "cpu": psutil.cpu_percent(interval=None),
                "mem": psutil.virtual_memory().percent,
                "disk": psutil.disk_usage(disk_root).percent,
            }
            await websocket.send_json(status)
            await asyncio.sleep(3)
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
