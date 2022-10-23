import asyncio
import logging
import websockets

from PIL import Image
from io import BytesIO
from aiogram import Bot
from aiogram.types import Message
from aiogram.utils import executor
from aiogram.dispatcher import Dispatcher
from aiogram.types import ContentTypes, PhotoSize
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from tg_bot.websocket_protocols import WebsocketImage, StartStyleTransferRequest, StyleTransferResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token="5379013202:AAGANHXLOw6EXfe_fnBo3-U2zuhMWfElOlE")
dispatcher = Dispatcher(bot, storage=MemoryStorage())


@dispatcher.message_handler(commands=["start"])
async def process_start_command(message: Message) -> None:
    await message.answer("Hello, I am neural style transfer bot! Just send me two images and enjoy the result!")


@dispatcher.message_handler(regexp=r"(/content_image)|(/style_image)", content_types=ContentTypes.PHOTO | ContentTypes.DOCUMENT)
async def process_set_image(message: Message) -> None:
    current_user_data = await dispatcher.storage.get_data(
        chat=message.chat.id,
        user=message.from_user.username,
    )

    current_user_data[message.get_command().split("_")[0][1:]] = message.photo[-1]
    await dispatcher.storage.set_data(
        chat=message.chat.id,
        user=message.from_user.username,
        data=current_user_data,
    )

    if message.get_command().startswith("/content"):
        await message.answer("Set content image successfully!")
    elif message.get_command().startswith("/style"):
        await message.answer("Set style image successfully!")


async def convert_photo_to_websocket_image(photo: PhotoSize) -> WebsocketImage:
    stream: BytesIO = BytesIO()
    await photo.download(destination_file=stream)

    bytes_array: bytes = Image.open(stream).tobytes()
    photo_size: tuple[int, int] = (photo.width, photo.height)
    return WebsocketImage(bytes_array, photo_size)


async def convert_websocket_image_to_bytes_stream(image: WebsocketImage) -> BytesIO:
    pil_image = image.to_pil_image()
    stream = BytesIO()
    stream.name = "img.jpg"
    pil_image.save(stream, "JPEG")
    stream.seek(0)
    return stream


@dispatcher.message_handler(commands=["start_nst"])
async def process_start_image_style_transfer(message: Message) -> None:
    user_data = await dispatcher.storage.get_data(chat=message.chat.id, user=message.from_user.username)
    content_image = await convert_photo_to_websocket_image(user_data["content"])
    style_image = await convert_photo_to_websocket_image(user_data["style"])

    try:
        async with websockets.connect("ws://localhost:8000/style_transfer") as websocket:
            request = StartStyleTransferRequest(
                message.from_user.username,
                content_image,
                style_image
            )
            await request.to_websocket(websocket)

            while True:
                response = await StyleTransferResponse.from_websocket(websocket)
                await message.answer_photo(await convert_websocket_image_to_bytes_stream(response.image))
    except Exception as e:
        logger.info(e)


if __name__ == "__main__":
    executor.start_polling(dispatcher, skip_updates=True)

