import yaml
import typing as tp

from aiogram import Bot
from aiogram.types import Message
from aiogram.utils import executor
from aiogram.types import ContentTypes
from aiogram.dispatcher import Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from backend.config import Config
from backend.logger import get_logger
from tg_bot.controller import stop_nst_controller, set_image_controller, start_style_transfer_controller, set_style_transfer_parameter


logger = get_logger(__name__)


with open(Config.path_to_backend / "../tg_bot/config.yaml", "r") as config_file:
    bot_config = yaml.safe_load(config_file)


bot = Bot(token=bot_config["token"])
dispatcher = Dispatcher(bot, storage=MemoryStorage())


@dispatcher.message_handler(commands=["start"])
async def process_start_command(message: Message) -> None:
    logger.debug(f"User {message.from_user.username} starts bot.")
    await message.answer("Hello, I am neural style transfer bot! Just send me two images and enjoy the result!")


@dispatcher.message_handler(commands=["stop_nst"])
async def process_stop_nst_command(message: Message) -> None:
    try:
        result: tp.Optional[str] = await stop_nst_controller(message.chat.id, message.from_user.username, dispatcher.storage)
        if result:
            await message.answer(result)
    except Exception as exc:
        await message.answer("Sorry, something went wrong during stopping transfer. Please try again.")
        logger.warning(f"{message.from_user.username}'s attempt to stop transfer is failed with exception", exc_info=exc)


@dispatcher.message_handler(regexp=r"(/content_image)|(/style_image)", content_types=ContentTypes.PHOTO | ContentTypes.DOCUMENT)
async def process_set_image(message: Message) -> None:
    image_type: str = message.get_command().split("_")[0][1:]
    try:
        result: str = await set_image_controller(message.chat.id, message.from_user.username, dispatcher.storage, image_type, message.photo)
        await message.answer(result)
    except Exception as exc:
        await message.answer("Sorry, something went wrong during saving photo. Please try again.")
        logger.warning(f"{message.from_user.username}'s attempt to set {image_type} image is failed with exception", exc_info=exc)


@dispatcher.message_handler(commands=["start_nst"])
async def process_start_image_style_transfer(message: Message) -> None:
    try:
        user_data: dict[str, tp.Any] = await dispatcher.storage.get_data(chat=message.chat.id, user=message.from_user.username)
        if ("content_image" not in user_data) or ("style_image" not in user_data):
            logger.debug(f"User {message.from_user.username} didn't provide content or style image. Transfer stopped.")
            await message.answer("Please, set content and style images using /content_image and /style_image commands.")
            return

        transfer_message: Message = await message.answer_photo(user_data["content_image"].file_id, caption="Starting transfer...")
        result: str = await start_style_transfer_controller(message.chat.id, message.from_user.username, dispatcher.storage, transfer_message)
        if result != "Transfer completed!":
            await message.answer(result)
    except Exception as exc:
        await message.answer("Sorry, something went wrong during transferring style. Please try again.")
        logger.warning(f"{message.from_user.username}'s attempt to transfer style is failed with exception", exc_info=exc)


@dispatcher.message_handler(commands=["set_alpha"])
async def process_set_alpha(message: Message) -> None:
    result: str = await set_style_transfer_parameter(message.chat.id, message.from_user.username,
                                                     dispatcher.storage, "alpha", message.get_args())
    await message.answer(result)


@dispatcher.message_handler(commands=["set_content_loss_layers_id"])
async def process_set_content_loss_layers_id(message: Message):
    result: str = await set_style_transfer_parameter(message.chat.id, message.from_user.username,
                                                     dispatcher.storage, "content_loss_layers_id", message.get_args())
    await message.answer(result)


@dispatcher.message_handler(commands=["set_style_loss_layers_id"])
async def process_set_style_loss_layers_id(message: Message):
    result: str = await set_style_transfer_parameter(message.chat.id, message.from_user.username,
                                                     dispatcher.storage, "style_loss_layers_id", message.get_args())
    await message.answer(result)


@dispatcher.message_handler(commands=["set_num_iteration"])
async def process_set_num_iteration(message: Message):
    result: str = await set_style_transfer_parameter(message.chat.id, message.from_user.username,
                                                     dispatcher.storage, "num_iteration", message.get_args())
    await message.answer(result)


if __name__ == "__main__":
    executor.start_polling(dispatcher, skip_updates=True)
