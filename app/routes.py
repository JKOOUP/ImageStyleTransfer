import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.websocket_protocols import StartStyleTransferRequest, StyleTransferResponse
from backend.transfer.transfer import StyleTransferProcessor


router = APIRouter()
event_loop = asyncio.get_event_loop()


@router.websocket("/style_transfer")
async def style_transfer_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        request = await StartStyleTransferRequest.from_websocket(websocket)

        processor = StyleTransferProcessor()
        processor.configure(
            content_image=request.content_image.to_pil_image(),
            style_image=request.style_image.to_pil_image(),
            num_iteration=30,
            collect_content_loss_layers=[3],
            collect_style_loss_layers=[0, 1, 2, 3],
        )

        transfer_style_task = event_loop.create_task(processor.transfer_style())
        await asyncio.sleep(0)

        while not transfer_style_task.done() or not transfer_style_task.cancelled():
            try:
                print("Try to send json!")
                await StyleTransferResponse.from_pil_image(await processor.get_current_image()).to_websocket(websocket)
                print("Sent json!")
            except AssertionError as e:
                print(e)
                break

            await asyncio.sleep(3)
    except WebSocketDisconnect:
        print("WebSocket disconnected!")
