from fastapi import APIRouter, WebSocket, WebSocketDisconnect
router = APIRouter()


@router.websocket("/style_transfer")
async def style_transfer_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            inp = await websocket.receive_text()
            await websocket.send_text(inp)
    except WebSocketDisconnect:
        print("WebSocket disconnected!")
