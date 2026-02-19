from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class ConvBlock(nn.Module):
    def __init__(self, c_in: int, c_out: int) -> None:
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(c_in, c_out, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(c_out),
            nn.ReLU(inplace=True),
            nn.Conv2d(c_out, c_out, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(c_out),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.block(x)


class TinyUNet(nn.Module):
    def __init__(
        self,
        in_channels: int = 5,
        out_channels: int = 24,
        base: int = 48,
        output_activation: str = "softplus",
    ) -> None:
        super().__init__()
        self.inc = ConvBlock(in_channels, base)
        self.down1 = nn.Sequential(nn.MaxPool2d(2), ConvBlock(base, base * 2))
        self.down2 = nn.Sequential(nn.MaxPool2d(2), ConvBlock(base * 2, base * 4))

        self.up1_conv = ConvBlock(base * 4 + base * 2, base * 2)
        self.up2_conv = ConvBlock(base * 2 + base, base)
        self.out = nn.Conv2d(base, out_channels, kernel_size=1)
        self.output_activation = str(output_activation).lower()
        self.softplus = nn.Softplus(beta=1.0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)

        x = F.interpolate(x3, size=x2.shape[-2:], mode="bilinear", align_corners=False)
        x = torch.cat([x, x2], dim=1)
        x = self.up1_conv(x)

        x = F.interpolate(x, size=x1.shape[-2:], mode="bilinear", align_corners=False)
        x = torch.cat([x, x1], dim=1)
        x = self.up2_conv(x)

        x = self.out(x)
        if self.output_activation == "softplus":
            return self.softplus(x)
        if self.output_activation == "identity":
            return x
        raise ValueError(f"Unsupported output_activation: {self.output_activation}")
