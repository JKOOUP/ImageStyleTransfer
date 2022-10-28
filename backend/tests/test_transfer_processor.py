import pytest
import typing as tp

from PIL import Image
from torch import Tensor

from backend.config import Config
from backend.transfer import StyleTransferProcessor


@pytest.fixture(scope="module")
def content_image() -> tp.Generator[Tensor, None, None]:
    with Image.open(Config.path_to_backend / "tests/test_data/content_img.png") as image:
        yield image


@pytest.fixture(scope="module")
def style_image() -> tp.Generator[Tensor, None, None]:
    with Image.open(Config.path_to_backend / "tests/test_data/style_img.png") as image:
        yield image


@pytest.mark.asyncio
async def test_style_transfer_processor(content_image: Image.Image, style_image: Image.Image) -> None:
    st_processor = StyleTransferProcessor()
    st_processor.configure("test_user", content_image, style_image, 50, [3], [0, 1, 2, 3], pretrained_model_type="vgg16")
    result: Image.Image = await st_processor.transfer_style()
    result.save(Config.path_to_backend / "tests/test_data/result.png", "PNG")
