import yaml
import logging
import websockets

from aiogram import Bot
from aiogram.types import Message
from aiogram.utils import executor
from aiogram.dispatcher import Dispatcher
from aiogram.types import ContentTypes, InputMediaPhoto, InputFile
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from tg_bot.websocket_protocols import WebsocketImage, StartStyleTransferRequest, StyleTransferResponse


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


with open("config.yaml", "r") as config_file:
    bot_config = yaml.safe_load(config_file)


bot = Bot(token=bot_config["token"])
dispatcher = Dispatcher(bot, storage=MemoryStorage())


@dispatcher.message_handler(commands=["start"])
async def process_start_command(message: Message) -> None:
    logger.debug(f"User {message.from_user.username} starts bot.")
    await message.answer("Hello, I am neural style transfer bot! Just send me two images and enjoy the result!")


@dispatcher.message_handler(commands=["stop_nst"])
async def process_stop_nst_command(message: Message) -> None:
    user_data = await dispatcher.storage.get_data(chat=message.chat.id, user=message.from_user.username)
    if not user_data.get("has_running_transfer", False):
        await message.answer("You haven't any transfer!")
        logger.debug(f"User {message.from_user.username} tried to stop transfer process without one.")
    else:
        user_data["stop_transfer"] = True
        await dispatcher.storage.set_data(chat=message.chat.id, user=message.from_user.username, data=user_data)


@dispatcher.message_handler(regexp=r"(/content_image)|(/style_image)", content_types=ContentTypes.PHOTO | ContentTypes.DOCUMENT)
async def process_set_image(message: Message) -> None:
    image_type: str = message.get_command().split("_")[0][1:]
    try:
        current_user_data = await dispatcher.storage.get_data(
            chat=message.chat.id,
            user=message.from_user.username,
        )

        if not message.photo:
            logger.debug(f"User {message.from_user.username} tried to set {image_type} with no provided photo!")
            await message.answer("Please, add photo to your message!")
            return

        current_user_data[image_type] = message.photo[-1]
        await dispatcher.storage.set_data(
            chat=message.chat.id,
            user=message.from_user.username,
            data=current_user_data,
        )

        if image_type == "content":
            await message.answer("Set content image successfully!")
            logger.debug(f"User {message.from_user.username} successfully set content image!")
        elif image_type == "style":
            await message.answer("Set style image successfully!")
            logger.debug(f"User {message.from_user.username} successfully set style image!")
    except Exception as exc:
        await message.answer("Sorry, something went wrong during saving photo. Please try again.")
        logger.warning(f"{message.from_user.username}'s attempt to set {image_type} image is failed with exception", exc_info=exc)


@dispatcher.message_handler(commands=["start_nst"])
async def process_start_image_style_transfer(message: Message) -> None:
    logger.debug(f"User {message.from_user.username} started style transfer.")
    user_data = await dispatcher.storage.get_data(chat=message.chat.id, user=message.from_user.username)
    try:
        if ("content" not in user_data) or ("style" not in user_data):
            await message.answer("Please, set content and style images using /content_image and /style_image commands.")
            logger.debug(f"User {message.from_user.username} didn't provide content or style image. Transfer stopped.")
            return

        user_data["has_running_transfer"] = True
        await dispatcher.storage.set_data(chat=message.chat.id, user=message.from_user.username, data=user_data)

        content_image = await WebsocketImage.from_telegram_photo(user_data["content"])
        style_image = await WebsocketImage.from_telegram_photo(user_data["style"])

        try:
            async with websockets.connect("ws://localhost:8000/style_transfer") as websocket:
                request = StartStyleTransferRequest(
                    message.from_user.username,
                    content_image,
                    style_image
                )
                await request.to_websocket(websocket)

                current_transfer_message: Message | None = None
                while True:
                    response = await StyleTransferResponse.from_websocket(websocket)

                    user_data = await dispatcher.storage.get_data(chat=message.chat.id, user=message.from_user.username)
                    if user_data.get("stop_transfer", False):
                        logger.debug(f"User {message.from_user.username} interrupted transfer.")
                        user_data["stop_transfer"] = False
                        await dispatcher.storage.set_data(chat=message.chat.id, user=message.from_user.username, data=user_data)
                        await message.answer(f"Successfully stop transferring!")
                        return

                    if current_transfer_message is None:
                        current_transfer_message = await message.answer_photo(await response.image.to_bytes_stream(), caption="Completed 0%")
                    else:
                        await current_transfer_message.edit_media(InputMediaPhoto(
                            InputFile(await response.image.to_bytes_stream()),
                            caption=f"Completed {response.completeness}%",
                        ))
        except websockets.ConnectionClosedOK:
            logger.debug(f"Transfer for user {message.from_user.username} ended successfully!")
    except Exception as exc:
        await message.answer("Sorry, something went wrong during transfer process. Please try again.")
        logger.warning(f"User {message.from_user.username} unsuccessfully attempted to transfer style", exc_info=exc)
    finally:
        user_data["has_running_transfer"] = False
        await dispatcher.storage.set_data(chat=message.chat.id, user=message.from_user.username, data=user_data)

if __name__ == "__main__":
    executor.start_polling(dispatcher, skip_updates=True)
