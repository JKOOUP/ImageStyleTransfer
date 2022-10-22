import torch
import torch.nn.functional


from backend.config import Config


class ContentLossLayer(torch.nn.Module):
    """
    Layer for computing content loss. It doesn't change input
    """
    def __init__(self, target: torch.Tensor) -> None:
        """
        :param target: feature map of original content image, [batch_size, C, H, W] tensor
        """
        assert len(target.shape) == 4, \
            f"Input tensor has to be [1, C, H, W], but {target.shape} met!"

        super().__init__()
        self.target: torch.Tensor = target
        self.loss: torch.Tensor = torch.tensor(0.0, device=Config.device)

    def forward(self, inp: torch.Tensor) -> torch.Tensor:
        """
        :param inp: [batch_size, C, H, W] tensor
        :return: inp without any changes
        """
        self.loss = torch.nn.functional.mse_loss(inp, self.target, reduction="mean")
        return inp


class StyleLossLayer(torch.nn.Module):
    """
    Layer for computing style loss. It doesn't change input
    """
    def __init__(self, target: torch.Tensor) -> None:
        """
        :param target: feature map of original style image, [1, C, H, W] tensor
        """
        assert len(target.shape) == 4, \
            f"Input tensor has to be [1, C, H, W], but {target.shape} met!"

        super().__init__()
        self.target_gram_matrix = self._gram_matrix(target).detach()
        self.loss: torch.Tensor = torch.tensor(0.0, device=Config.device)

    def forward(self, inp: torch.Tensor) -> torch.Tensor:
        """
        :param inp: [1, C, H, W] tensor
        :return: inp without any changes
        """
        gram_matrix: torch.Tensor = self._gram_matrix(inp)
        self.loss = torch.nn.functional.mse_loss(gram_matrix, self.target_gram_matrix, reduction="mean")
        return inp

    @staticmethod
    def _gram_matrix(tensor: torch.Tensor) -> torch.Tensor:
        """
        Reshapes input tensor to 2d-matrix and computes the Gram matrix
        :param tensor: [1, C, H, W] tensor
        :return: [C, H * W] tensor - the Gram matrix
        """
        bs, c, h, w = tensor.size()
        matrix: torch.Tensor = tensor.view(bs * c, h * w)
        result: torch.Tensor = torch.mm(matrix, matrix.t()).div(bs * c * h * w)
        return result
