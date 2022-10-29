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
    num_iteration: int
    content_loss_layers_id: list[int]
    style_loss_layers_id: list[int]
    alpha: float

    @staticmethod
    async def from_websocket(websocket: WebSocket) -> "StartStyleTransferRequest":
        username = await websocket.receive_text()
        content_image = await WebsocketImage.from_websocket(websocket)
        style_image = await WebsocketImage.from_websocket(websocket)
        num_iteration = int(await websocket.receive_text())
        content_loss_layers_id = [int(elem) for elem in (await websocket.receive_text()).split()]
        style_loss_layers_id = [int(elem) for elem in (await websocket.receive_text()).split()]
        alpha = float(await websocket.receive_text())
        return StartStyleTransferRequest(username, content_image, style_image, num_iteration, content_loss_layers_id, style_loss_layers_id, alpha)

    async def to_websocket(self, websocket: WebSocket) -> None:
        await websocket.send_text(self.username)
        await self.content_image.to_websocket(websocket)
        await self.style_image.to_websocket(websocket)
        await websocket.send_text(str(self.num_iteration))
        await websocket.send_text(" ".join(*self.content_loss_layers_id))
        await websocket.send_text(" ".join(*self.style_loss_layers_id))
        await websocket.send_text(str(self.alpha))


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
