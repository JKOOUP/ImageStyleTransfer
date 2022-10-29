import logging
import websockets
import typing as tp

from aiogram.contrib.fsm_storage.memory import BaseStorage
from aiogram.types import PhotoSize, Message, InputFile, InputMediaPhoto
from websockets.legacy.client import WebSocketClientProtocol as WebSocket

from backend.config import Config
from tg_bot.exceptions import TransferStoppedException, ContentOrStyleImageNotSetException
from tg_bot.websocket_protocols import WebsocketImage, StartStyleTransferRequest, StyleTransferResponse

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def stop_nst_controller(chat_id: int, username: str, storage: BaseStorage) -> tp.Optional[str]:
    user_data: dict[str, tp.Any] = await storage.get_data(chat=chat_id, user=username)
    if not user_data.get("has_running_transfer", False):
        logger.debug(f"User {username} tried to stop transfer process without one.")
        return "You haven't any transfer!"
    else:
        user_data["stop_transfer"] = True
        await storage.set_data(chat=chat_id, user=username, data=user_data)


async def set_image_controller(chat_id: int, username: str, storage: BaseStorage, image_type: str, photo: list[PhotoSize]) -> str:
    if not photo:
        logger.debug(f"User {username} tried to set {image_type} with no provided photo.")
        return "Please, add photo to your message!"

    user_data: dict[str, tp.Any] = await storage.get_data(chat=chat_id, user=username)
    user_data[image_type + "_image"] = photo[-1]
    await storage.set_data(chat=chat_id, user=username, data=user_data)

    if image_type == "content":
        logger.debug(f"User {username} successfully set content image.")
        return "Set content image successfully!"
    else:
        logger.debug(f"User {username} successfully set style image.")
        return "Set style image successfully!"


async def get_images_for_style_transfer(chat_id: int, username: str, storage: BaseStorage) -> tuple[WebsocketImage, WebsocketImage]:
    logger.debug(f"User {username} started style transfer.")
    user_data: dict[str, tp.Any] = await storage.get_data(chat=chat_id, user=username)

    if ("content_image" not in user_data) or ("style_image" not in user_data):
        logger.debug(f"User {username} didn't provide content or style image. Transfer stopped.")
        raise ContentOrStyleImageNotSetException("Content or style image is not set.")

    user_data["has_running_transfer"] = True
    await storage.set_data(chat=chat_id, user=username, data=user_data)

    content_image: WebsocketImage = await WebsocketImage.from_telegram_photo(user_data["content_image"])
    style_image: WebsocketImage = await WebsocketImage.from_telegram_photo(user_data["style_image"])
    return content_image, style_image


async def receive_intermediate_style_transfer_results(chat_id: int, username: str, storage: BaseStorage, websocket: WebSocket) \
        -> tp.Generator[InputMediaPhoto, None, None]:
    current_completeness: int = 0
    while current_completeness < 100:
        style_transfer_response: StyleTransferResponse = await StyleTransferResponse.from_websocket(websocket)
        current_completeness = style_transfer_response.completeness

        user_data: dict[str, tp.Any] = await storage.get_data(chat=chat_id, user=username)
        if user_data.get("stop_transfer", False):
            logger.debug(f"User {username} start interrupting transfer.")
            user_data["stop_transfer"] = False
            await storage.set_data(chat=chat_id, user=username, data=user_data)
            raise TransferStoppedException("User stopped transfer process.")

        yield InputMediaPhoto(
            InputFile(await style_transfer_response.image.to_bytes_stream()),
            caption=f"Completed {style_transfer_response.completeness}%",
        )


async def start_style_transfer_controller(chat_id: int, username: str, storage: BaseStorage, transfer_message: Message) -> str:
    try:
        content_image, style_image = await get_images_for_style_transfer(chat_id, username, storage)
    except ContentOrStyleImageNotSetException:
        return "Please, set content and style images using /content_image and /style_image commands."

    result_message: str = "Transfer completed!"
    try:
        async with websockets.connect(f"ws://localhost:{Config.backend_port}/style_transfer") as websocket:
            request = StartStyleTransferRequest(username, content_image, style_image)
            await request.to_websocket(websocket)

            async for media_photo in receive_intermediate_style_transfer_results(chat_id, username, storage, websocket):
                await transfer_message.edit_media(media_photo)
            logger.debug(f"User {username} successfully transferred style.")
    except TransferStoppedException:
        logger.debug(f"User {username} successfully interrupted transfer.")
        result_message = "Successfully stopped transfer!"
    except websockets.ConnectionClosed as exc:
        logger.debug(f"User {username} disconnected!", exc_info=exc)
        result_message = "Sorry, something went wrong during transfer process. Please try again."
    except Exception as exc:
        logger.warning(f"User {username} unsuccessfully attempted to transfer style", exc_info=exc)
        result_message = "Sorry, something went wrong during transfer process. Please try again."
    finally:
        user_data: dict[str, tp.Any] = await storage.get_data(chat=chat_id, user=username)
        user_data["has_running_transfer"] = False
        await storage.set_data(chat=chat_id, user=username, data=user_data)
    return result_message
