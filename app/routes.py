import asyncio
import typing as tp

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.logger import get_logger
from app.websocket_protocols import StartStyleTransferRequest, StyleTransferResponse
from app.controllers import style_transfer_ws_controller

router = APIRouter()
logger = get_logger(__name__)


@router.websocket("/style_transfer")
async def style_transfer_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    username: tp.Optional[str] = None
    style_transfer_task: tp.Optional[asyncio.Task] = None

    try:
        request = await StartStyleTransferRequest.from_websocket(websocket)
        username = request.username
        logger.info("Got request for style transfer.", extra={"username": username})

        response_generator: tp.AsyncGenerator[tp.Optional[asyncio.Task, StyleTransferResponse], None] = style_transfer_ws_controller(request)
        style_transfer_task: asyncio.Task = await anext(response_generator)
        async for response in response_generator:
            await response.to_websocket(websocket)
    except AssertionError as exc:
        logger.warning("Style transfer failed with exception.", exc_info=exc, extra={"username": username})
    except WebSocketDisconnect:
        logger.info("User disconnected.", extra={"username": username})
    finally:
        if style_transfer_task and (not style_transfer_task.done()):
            style_transfer_task.cancel()
            logger.info("Style transfer task was cancelled.", extra={"username": username})
        await websocket.close()
