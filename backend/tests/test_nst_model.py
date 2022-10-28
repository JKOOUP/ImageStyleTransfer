import torch
import pytest
import typing as tp

from PIL import Image
from torch import Tensor
from torch.nn import Conv2d

from backend.config import Config
from backend.transfer import NSTModel
from backend.transfer import ContentLossLayer, StyleLossLayer


@pytest.fixture(scope="module")
def content_image() -> tp.Generator[Tensor, None, None]:
    with Image.open(Config.path_to_backend / "tests/test_data/content_img.png") as image:
        yield image


@pytest.fixture(scope="module")
def style_image() -> tp.Generator[Tensor, None, None]:
    with Image.open(Config.path_to_backend / "tests/test_data/style_img.png") as image:
        yield image


@pytest.fixture(scope="module")
def model(content_image: Image.Image, style_image: Image.Image) -> tp.Generator[torch.nn.Module, None, None]:
    yield NSTModel("test_user", content_image, style_image)


def test_nst_model_structure(model: torch.nn.Module) -> None:
    assert len(list(model._model.children())) == 37

    num_conv_layers: int = len([elem for elem in model._model.children() if isinstance(elem, Conv2d)])
    num_content_loss_layers: int = len([elem for elem in model._model.children() if isinstance(elem, ContentLossLayer)])
    num_style_loss_layers: int = len([elem for elem in model._model.children() if isinstance(elem, StyleLossLayer)])

    assert num_content_loss_layers == num_conv_layers
    assert num_style_loss_layers == num_conv_layers
    assert len(model._content_loss_layers) == num_content_loss_layers
    assert len(model._style_loss_layers) == num_style_loss_layers


def test_nst_model_collects_gradients(model: torch.nn.Module, content_image: Image.Image) -> None:
    input_img: Tensor = torch.randn(1, 3, *Config.working_image_size, requires_grad=True)

    model(input_img)

    cumulative_style_loss: Tensor = torch.tensor(0.0)
    for style_layer in model._style_loss_layers:
        cumulative_style_loss += style_layer.loss
        assert style_layer.loss.item() != pytest.approx(0.0, abs=1e-6)

    cumulative_content_loss: Tensor = torch.tensor(0.0)
    for content_layer in model._content_loss_layers:
        cumulative_content_loss += content_layer.loss
        assert content_layer.loss.item() != pytest.approx(0.0, abs=1e-6)

    loss = cumulative_style_loss + cumulative_content_loss
    loss.backward()

    assert input_img.grad is not None
    assert input_img.grad.data != pytest.approx(torch.zeros_like(input_img.grad.data), abs=1e-6)
