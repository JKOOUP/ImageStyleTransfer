from PIL import Image
from fastapi import WebSocket
from dataclasses import dataclass


@dataclass
class WebsocketImage:
    bytes_array: bytes
    size: tuple[int, int]

    @staticmethod
    async def from_websocket(websocket: WebSocket) -> "WebsocketImage":
        size_text = (await websocket.receive_text()).split()
        size = (int(size_text[0]), int(size_text[1]))
        bytes_array = await websocket.receive_bytes()
        return WebsocketImage(bytes_array, size)

    async def to_websocket(self, websocket: WebSocket) -> None:
        await websocket.send_text(str(self.size[0]) + " " + str(self.size[1]))
        await websocket.send_bytes(self.bytes_array)

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
        username = await websocket.receive_text()
        content_image = await WebsocketImage.from_websocket(websocket)
        style_image = await WebsocketImage.from_websocket(websocket)
        return StartStyleTransferRequest(username, content_image, style_image)

    async def to_websocket(self, websocket: WebSocket) -> None:
        await websocket.send_text(self.username)
        await self.content_image.to_websocket(websocket)
        await self.style_image.to_websocket(websocket)


@dataclass
class StyleTransferResponse:
    image: WebsocketImage
    completeness: int

    @staticmethod
    async def from_websocket(websocket: WebSocket) -> "StyleTransferResponse":
        image: WebsocketImage = await WebsocketImage.from_websocket(websocket)
        completeness: int = int(await websocket.receive_text())
        return StyleTransferResponse(image, completeness)

    async def to_websocket(self, websocket: WebSocket) -> None:
        await self.image.to_websocket(websocket)
        await websocket.send_text(str(self.completeness))

    @staticmethod
    def from_pil_image(img: Image.Image, completeness: int = 0) -> "StyleTransferResponse":
        return StyleTransferResponse(WebsocketImage.from_pil_image(img), completeness)

    def to_pil_image(self) -> Image.Image:
        return self.image.to_pil_image()
