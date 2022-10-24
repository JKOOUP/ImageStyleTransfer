from PIL import Image
from io import BytesIO
from dataclasses import dataclass
from aiogram.types import PhotoSize
from websockets.legacy.client import WebSocketClientProtocol as WebSocket


@dataclass
class WebsocketImage:
    bytes_array: bytes
    size: tuple[int, int]

    @staticmethod
    async def from_websocket(websocket: WebSocket) -> "WebsocketImage":
        size_text: list[str] = (await websocket.recv()).split()
        size: tuple[int, int] = (int(size_text[0]), int(size_text[1]))
        bytes_array: bytes = await websocket.recv()
        return WebsocketImage(bytes_array, size)

    async def to_websocket(self, websocket: WebSocket) -> None:
        await websocket.send(str(self.size[0]) + " " + str(self.size[1]))
        await websocket.send(self.bytes_array)

    @staticmethod
    def from_pil_image(img: Image.Image) -> Image:
        bytes_array = img.tobytes()
        size = img.size
        return WebsocketImage(bytes_array, size)

    @staticmethod
    async def from_telegram_photo(photo: PhotoSize) -> "WebsocketImage":
        stream: BytesIO = BytesIO()
        await photo.download(destination_file=stream)

        bytes_array: bytes = Image.open(stream).tobytes()
        photo_size: tuple[int, int] = (photo.width, photo.height)
        return WebsocketImage(bytes_array, photo_size)

    async def to_bytes_stream(self) -> BytesIO:
        pil_image: Image.Image = self.to_pil_image()
        stream: BytesIO = BytesIO()
        stream.name = "img.jpg"
        pil_image.save(stream, "JPEG")
        stream.seek(0)
        return stream

    def to_pil_image(self) -> Image:
        return Image.frombytes("RGB", self.size, self.bytes_array)


@dataclass
class StartStyleTransferRequest:
    username: str
    content_image: WebsocketImage
    style_image: WebsocketImage

    @staticmethod
    async def from_websocket(websocket: WebSocket) -> "StartStyleTransferRequest":
        username: str = await websocket.recv()
        content_image: WebsocketImage = await WebsocketImage.from_websocket(websocket)
        style_image: WebsocketImage = await WebsocketImage.from_websocket(websocket)
        return StartStyleTransferRequest(username, content_image, style_image)

    async def to_websocket(self, websocket: WebSocket) -> None:
        await websocket.send(self.username)
        await self.content_image.to_websocket(websocket)
        await self.style_image.to_websocket(websocket)


@dataclass
class StyleTransferResponse:
    image: WebsocketImage
    completeness: int

    @staticmethod
    async def from_websocket(websocket: WebSocket) -> "StyleTransferResponse":
        image: WebsocketImage = await WebsocketImage.from_websocket(websocket)
        completeness: int = int(await websocket.recv())
        return StyleTransferResponse(image, completeness)

    async def to_websocket(self, websocket: WebSocket) -> None:
        await self.image.to_websocket(websocket)
        await websocket.send(str(self.completeness))

    @staticmethod
    def from_pil_image(img: Image.Image, completeness: int = 0) -> "StyleTransferResponse":
        return StyleTransferResponse(WebsocketImage.from_pil_image(img), completeness)

    def to_pil_image(self) -> Image.Image:
        return self.image.to_pil_image()
