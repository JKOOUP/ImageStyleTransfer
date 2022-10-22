import torch
import torch.nn as nn
import typing as tp

from torch import Tensor
from pathlib import Path
from PIL.Image import Image
from torchvision.transforms import Compose, Normalize, ToTensor, Resize
from torchvision.models import vgg11, vgg13, vgg16, vgg19
from torchvision.models import VGG11_Weights, VGG13_Weights, VGG16_Weights, VGG19_Weights

from backend.config import Config
from backend.transfer.layers import ContentLossLayer, StyleLossLayer


class NSTModel(nn.Module):
    """
    Model for neural style transfer
    """
    def __init__(self,
                 content_image: Image,
                 style_image: Image,
                 pretrained_model_type: str = "vgg11",
                 path_to_save_dir: Path = Config.path_to_backend / "./transfer/pretrained") -> None:
        """
        Initialize NSTModel
        :param content_image: content image
        :param style_image: style image
        :param path_to_save_dir: path for downloading pretrained model
        """
        self._initialize_available_models()
        assert pretrained_model_type in self._available_base_models.keys(), \
            f"Only {self._available_base_models.keys()} is available for base model"

        super().__init__()
        self._pretrained_model_type: str = pretrained_model_type
        self._path_to_save_dir: Path = path_to_save_dir

        self._transforms = Compose([
            ToTensor(),
            Normalize(mean=Config.normalization_mean, std=Config.normalization_std),
            Resize(Config.working_image_size),
        ])

        self._content_loss_layers: list[ContentLossLayer] = []
        self._style_loss_layers: list[StyleLossLayer] = []
        self._model = self._build_model(content_image, style_image, pretrained_model_type)

    def forward(self, inp: Tensor) -> Tensor:
        """
        Forwards input tensor through the model
        :param inp: input tensor
        :return: output of the model
        """
        output = self._model(inp)
        return output

    def collect_loss(self,
                     collect_content_loss_layers: list[int],
                     collect_style_loss_layers: list[int],
                     alpha: torch.Tensor = Config.alpha) -> Tensor:
        """
        Computes content and style loss for previously forwarded tensor
        :param collect_content_loss_layers: list of indexes of content loss layers whose loss will be taken into account
        :param collect_style_loss_layers: list of indexes of style loss layers whose loss will be taken into account
        :param alpha: style loss coefficient in total loss
        :return: total loss of previously forwarded tensor
        """
        content_loss: Tensor = torch.tensor(0.0, device=Config.device)
        for layer_idx in collect_content_loss_layers:
            content_loss += self._content_loss_layers[layer_idx].loss
        content_loss /= len(collect_content_loss_layers)

        style_loss: Tensor = torch.tensor(0.0, device=Config.device)
        for layer_idx in collect_style_loss_layers:
            style_loss += self._style_loss_layers[layer_idx].loss
        style_loss /= len(collect_style_loss_layers)

        print(f"Content loss: {content_loss.item():.6f}")
        print(f"Style loss: {style_loss.item():.6f}")

        loss: Tensor = content_loss + alpha * style_loss
        return loss

    def cut_model(self, conv_layer_idx: int) -> None:
        """
        Cuts all layers of the model after conv_layer_idx convolutional layers
        :param conv_layer_idx: number of convolutional layers that has to be preserved
        """
        for model_layer_idx, layer in enumerate(self._model.children()):
            if isinstance(layer, nn.Conv2d):
                conv_layer_idx -= 1
            if conv_layer_idx + 1 == 0:
                self._model = self._model[:model_layer_idx + 2]
                return

    def _initialize_available_models(self) -> None:
        """
        Initializes available base models for neural style transfer. Adds two dictionaries. first contains mapping from
        model_type (str) to torch function that loads pretrained base model. Second contains mapping from model_type to
        pretrained weights.
        """
        self._available_base_models: dict[str, tp.Any] = {
            "vgg11": vgg11,
            "vgg13": vgg13,
            "vgg16": vgg16,
            "vgg17": vgg19,
        }
        self._available_base_models_weights: dict[str, tp.Any] = {
            "vgg11": VGG11_Weights.DEFAULT,
            "vgg13": VGG13_Weights.DEFAULT,
            "vgg16": VGG16_Weights.DEFAULT,
            "vgg19": VGG19_Weights.DEFAULT,
        }

    def _build_model(self, content_image: Image, style_image: Image, pretrained_model_type: str) -> nn.Module:
        """
        Builds model that will be used for neural style_transfer
        :param content_image: content image
        :param style_image: style image
        :param pretrained_model_type: pretrained model type
        :return: neural style transfer model
        """
        base_model: nn.Module = self._load_pretrained_base_model(pretrained_model_type)
        result = nn.Sequential()

        current_content_tensor: Tensor = self._transforms(content_image).unsqueeze(0)
        current_style_tensor: Tensor = self._transforms(style_image).unsqueeze(0)

        idx: int = 0
        for layer in base_model.children():
            current_content_tensor = layer(current_content_tensor)
            current_style_tensor = layer(current_style_tensor)
            if isinstance(layer, nn.Conv2d):
                result.append(layer)
                result.append(ContentLossLayer(current_content_tensor))
                self._content_loss_layers.append(result[-1])
                result.append(StyleLossLayer(current_style_tensor))
                self._style_loss_layers.append(result[-1])
                idx += 1
            elif isinstance(layer, nn.ReLU):
                result.append(nn.ReLU())
            else:
                result.append(layer)
        return result

    def _load_pretrained_base_model(self, model_type: str) -> nn.Module:
        """
        Loads selected pretrained model from torch hub. Now only vgg16 and vgg19 is implemented
        :param model_type: type of base model.
        :return: base model.
        """
        path_to_pretrained: Path = Config.path_to_backend / self._path_to_save_dir
        if not path_to_pretrained.exists():
            path_to_pretrained.mkdir(parents=True, exist_ok=True)

        torch.hub.set_dir(str(path_to_pretrained))
        if model_type.startswith("vgg"):
            base_model: nn.Module = self._available_base_models[model_type](
                weights=self._available_base_models_weights[model_type]
            ).eval().features
        else:
            raise NotImplementedError("Only vgg models available as base models!")
        return base_model
