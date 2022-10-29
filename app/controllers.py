import asyncio
import typing as tp

from PIL.Image import Image
from asyncio import CancelledError

from backend.logger import get_logger
from backend.transfer import StyleTransferProcessor
from app.websocket_protocols import StartStyleTransferRequest, StyleTransferResponse


event_loop = asyncio.get_event_loop()
logger = get_logger(__name__)


def configure_style_transfer_processor(username: str, content_image: Image, style_image: Image, num_iteration: int,
                                       content_loss_layers_id: list[int], style_loss_layers_id: list[int], alpha: float) -> StyleTransferProcessor:
    processor = StyleTransferProcessor()
    try:
        processor.configure(
            username=username,
            content_image=content_image,
            style_image=style_image,
            num_iteration=num_iteration,
            collect_content_loss_layers=content_loss_layers_id,
            collect_style_loss_layers=style_loss_layers_id,
            alpha=alpha,
        )
    except AssertionError as exc:
        logger.warning("Tried to configure processor with incorrect params.", exc_info=exc)
        raise
    return processor


async def current_states_generator(
        style_transfer_task: asyncio.Task,
        processor: StyleTransferProcessor,
        username: str,
        sleep_time: int) -> tp.AsyncGenerator[StyleTransferResponse, None]:
    while (not style_transfer_task.done() or not style_transfer_task.cancelled()) and processor.is_transferring():
        try:
            response: StyleTransferResponse = StyleTransferResponse.from_pil_image(
                processor.get_current_image(),
                processor.get_current_transfer_status(),
            )
            yield response
        except AssertionError as exc:
            logger.warning("Tried to get current style transfer result, but there's no transfer.",
                           extra={"username": username}, exc_info=exc)
            style_transfer_task.cancel()
            raise
        await asyncio.sleep(sleep_time)


def get_style_transfer_task_result(username: str, style_transfer_task: asyncio.Task) -> tp.Optional[StyleTransferResponse]:
    try:
        result: Image = style_transfer_task.result()
        return StyleTransferResponse.from_pil_image(result, completeness=100)
    except CancelledError:
        logger.warning("Failed to get transfer style task result, since task was cancelled.", extra={"username": username})
        raise
    except Exception as exc:
        logger.warning("Transfer style task failed with exception.", exc_info=exc, extra={"username": username})
        raise


async def style_transfer_ws_controller(request: StartStyleTransferRequest) \
        -> tp.AsyncGenerator[tp.Union[asyncio.Task, StyleTransferResponse], None]:
    processor: StyleTransferProcessor = configure_style_transfer_processor(
        username=request.username,
        content_image=request.content_image.to_pil_image(),
        style_image=request.style_image.to_pil_image(),
        num_iteration=request.num_iteration,
        content_loss_layers_id=request.content_loss_layers_id,
        style_loss_layers_id=request.style_loss_layers_id,
        alpha=request.alpha,
    )

    style_transfer_task: asyncio.Task = event_loop.create_task(processor.transfer_style())
    logger.debug("Started style transfer task.", extra={"username": request.username})
    yield style_transfer_task

    await asyncio.sleep(0)

    async for response in current_states_generator(style_transfer_task, processor, request.username, 1):
        yield response
        logger.debug(f"Sent response with completeness = {response.completeness}%.", extra={"username": request.username})

    final_response: tp.Optional[StyleTransferResponse] = get_style_transfer_task_result(request.username, style_transfer_task)
    if final_response:
        yield final_response
        logger.debug("Sent final response.", extra={"username": request.username})
