from PIL import Image
from websockets.legacy.client import WebSocketClientProtocol as WebSocket
from dataclasses import dataclass


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

    @staticmethod
    async def from_websocket(websocket: WebSocket) -> "StyleTransferResponse":
        return StyleTransferResponse(await WebsocketImage.from_websocket(websocket))

    async def to_websocket(self, websocket: WebSocket) -> None:
        await self.image.to_websocket(websocket)

    @staticmethod
    def from_pil_image(img: Image.Image) -> "StyleTransferResponse":
        return StyleTransferResponse(WebsocketImage.from_pil_image(img))

    def to_pil_image(self) -> Image.Image:
        return self.image.to_pil_image()
