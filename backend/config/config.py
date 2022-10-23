import torch

from pathlib import Path


class Config:
    # Path to backend package
    path_to_backend: Path = Path().cwd().parent.absolute().resolve()

    # The device on which the calculations take place
    # Default value depends on your system (GPU or CPU)
    device: torch.device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")

    # Mean and std for normalization of input to pretrained network. Calculated on ImageNet data.
    normalization_mean: torch.Tensor = torch.tensor([0.485, 0.456, 0.406]).view(-1, 1, 1).to(device)
    normalization_std: torch.Tensor = torch.tensor([0.229, 0.224, 0.225]).view(-1, 1, 1).to(device)

    # Before style transfer, input images will be resized to this size.
    working_image_size: tuple[int, int] = (256, 256)

    # Style loss coefficient in total loss
    alpha: torch.Tensor = torch.tensor(10000, device=device)

    # Enable debug mode
    debug: bool = False
