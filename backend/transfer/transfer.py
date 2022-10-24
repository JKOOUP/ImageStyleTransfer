import asyncio
import typing as tp

from torch import Tensor
from PIL.Image import Image
from torch.optim import Optimizer, Adam
from torchvision.transforms import Compose, Normalize, ToTensor, ToPILImage, Resize

from backend.config import Config
from backend.logger import get_logger
from backend.transfer import NSTModel


logger = get_logger(__name__)


class StyleTransferProcessor:
    def __init__(self) -> None:
        self._username: tp.Optional[str] = None
        self._nst_model: tp.Optional[NSTModel] = None
        self._input_tensor: tp.Optional[Tensor] = None
        self._optimizer: tp.Optional[Optimizer] = None
        self._num_iteration: tp.Optional[int] = None
        self._collect_content_loss_layers: tp.Optional[list[int]] = None
        self._collect_style_loss_layers: tp.Optional[list[int]] = None
        self._init_content_image_size: tp.Optional[tuple[int, int]] = None
        self._transfer_status: int = 0

    def configure(self,
                  username: str,
                  content_image: Image,
                  style_image: Image,
                  num_iteration: int,
                  collect_content_loss_layers: list[int],
                  collect_style_loss_layers: list[int],
                  pretrained_model_type: str = "vgg11") -> "StyleTransferProcessor":
        self._username = username
        self._nst_model = NSTModel(content_image, style_image, pretrained_model_type=pretrained_model_type)

        self._input_tensor = Compose([
            ToTensor(),
            Normalize(mean=Config.normalization_mean, std=Config.normalization_std),
            Resize(Config.working_image_size),
        ])(content_image).view(1, 3, *Config.working_image_size)
        self._input_tensor.requires_grad = True

        self._optimizer = Adam([self._input_tensor], lr=0.01)
        self._num_iteration = num_iteration
        self._collect_content_loss_layers = collect_content_loss_layers
        self._collect_style_loss_layers = collect_style_loss_layers
        self._nst_model.cut_model(max(self._collect_style_loss_layers + self._collect_content_loss_layers))
        self._init_content_image_size = content_image.size
        logger.info(f"[{self._username}][StyleTransferProcessor was successfully configured.]")
        return self

    async def get_current_image(self) -> Image:
        assert self._input_tensor is not None, "StyleTransferProcessor is not configured! Call configure() method!"
        assert self._transfer_status != 0, "StyleTransferProcessor isn't transferring now!"

        logger.info(f"[{self._username}][Get current style transfer result.]")

        current_img_tensor: Tensor = self._input_tensor.detach() * Config.normalization_std + Config.normalization_mean
        current_img_tensor = current_img_tensor.clamp(0, 1).squeeze(0)
        return Compose([
            Resize(self._init_content_image_size),
            ToPILImage(),
        ])(current_img_tensor)

    def get_current_transfer_status(self) -> int:
        return 100 * self._transfer_status // self._num_iteration

    async def transfer_style(self) -> Image:
        logger.info(f"[{self._username}][Started style transfer process.]")
        for iteration_idx in range(self._num_iteration):
            self._transfer_status = iteration_idx + 1

            await asyncio.sleep(0)
            await self._process_transfer_iteration()

            if (iteration_idx + 1) % (self._num_iteration // 10) == 0:
                logger.info(f"[{self._username}][Completed {100 * (iteration_idx + 1) / self._num_iteration:.2f}%]")

        result: Image = await self.get_current_image()
        self._transfer_status = 0
        logger.info(f"[{self._username}][Ended style transfer process.]")
        return result

    async def _process_transfer_iteration(self) -> None:
        assert self._nst_model is not None, "StyleTransferProcessor is not configured! Call configure() method!"
        self._optimizer.zero_grad()
        self._nst_model(self._input_tensor)
        loss: Tensor = self._nst_model.collect_loss(self._collect_content_loss_layers, self._collect_style_loss_layers)
        loss.backward(retain_graph=True)
        self._optimizer.step()
