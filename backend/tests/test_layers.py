import torch
import pytest
import typing as tp

from PIL import Image
from torch import Tensor
from torchvision.transforms import Compose, Normalize, ToTensor

from backend.config import Config
from backend.transfer import ContentLossLayer, StyleLossLayer


@pytest.fixture(scope="module")
def tensor_image() -> tp.Generator[torch.Tensor, None, None]:
    with Image.open("./test_data/img.png") as image:
        transforms = Compose([
            ToTensor(),
            Normalize(mean=Config.normalization_mean, std=Config.normalization_std),
        ])
        tensor_image: Tensor = transforms(image.crop((50, 50, 250, 250)))
        tensor_image = tensor_image.view(-1, *tensor_image.shape).to(Config.device)
        yield tensor_image


@pytest.mark.parametrize("layer_class", [ContentLossLayer, StyleLossLayer])
def test_style_and_content_loss_layers(tensor_image: torch.Tensor, layer_class: tp.Union[ContentLossLayer, StyleLossLayer]) -> None:
    layer: ContentLossLayer = layer_class(tensor_image)
    layer_output: torch.Tensor = layer(tensor_image)

    assert layer_output.shape == tensor_image.shape
    assert layer_output.cpu() == pytest.approx(tensor_image.cpu(), abs=1e-6)
    assert layer.loss.item() == pytest.approx(0.0, abs=1e-6)

    random_input: Tensor = torch.randn_like(tensor_image, device=Config.device)
    layer_output = layer(random_input)

    assert layer_output.shape == tensor_image.shape
    assert layer_output.cpu() == pytest.approx(random_input.cpu(), abs=1e-6)
    assert layer.loss.item() != pytest.approx(0.0, abs=1e-6)
