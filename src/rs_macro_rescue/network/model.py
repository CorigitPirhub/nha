from __future__ import annotations

from typing import Literal, cast

import torch
import torch.nn as nn
import torch.nn.functional as F

OutputActivation = Literal["softplus", "identity"]


class SEBlock(nn.Module):
    def __init__(self, channels: int, reduction: int = 8) -> None:
        super().__init__()
        hidden = max(channels // max(reduction, 1), 4)
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Sequential(
            nn.Conv2d(channels, hidden, kernel_size=1, bias=True),
            nn.ReLU(inplace=True),
            nn.Conv2d(hidden, channels, kernel_size=1, bias=True),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        w = self.fc(self.pool(x))
        return x * w


class ConvBlock(nn.Module):
    def __init__(self, c_in: int, c_out: int, use_se: bool = False, dilation: int = 1) -> None:
        super().__init__()
        d = int(max(dilation, 1))
        layers: list[nn.Module] = [
            nn.Conv2d(c_in, c_out, kernel_size=3, padding=d, dilation=d, bias=False),
            nn.BatchNorm2d(c_out),
            nn.ReLU(inplace=True),
            nn.Conv2d(c_out, c_out, kernel_size=3, padding=d, dilation=d, bias=False),
            nn.BatchNorm2d(c_out),
            nn.ReLU(inplace=True),
        ]
        if use_se:
            layers.append(SEBlock(c_out))
        self.block = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.block(x)


class TinyUNet(nn.Module):
    def __init__(
        self,
        in_channels: int = 5,
        out_channels: int = 24,
        base: int = 48,
        output_activation: OutputActivation = "softplus",
    ) -> None:
        super().__init__()
        self.inc = ConvBlock(in_channels, base, use_se=False)
        self.down1 = nn.Sequential(nn.MaxPool2d(2), ConvBlock(base, base * 2, use_se=False))
        self.down2 = nn.Sequential(nn.MaxPool2d(2), ConvBlock(base * 2, base * 4, use_se=False))

        self.up1_conv = ConvBlock(base * 4 + base * 2, base * 2, use_se=False)
        self.up2_conv = ConvBlock(base * 2 + base, base, use_se=False)
        self.out = nn.Conv2d(base, out_channels, kernel_size=1)
        act = str(output_activation).lower()
        if act not in {"softplus", "identity"}:
            raise ValueError(f"Unsupported output_activation: {output_activation}")
        self.output_activation = cast(OutputActivation, act)
        self.softplus = nn.Softplus(beta=1.0)

    def _apply_output_activation(self, x: torch.Tensor) -> torch.Tensor:
        if self.output_activation == "softplus":
            return self.softplus(x)
        if self.output_activation == "identity":
            return x
        raise ValueError(f"Unsupported output_activation: {self.output_activation}")

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
        return self._apply_output_activation(x)


class PyramidPooling(nn.Module):
    def __init__(self, c_in: int, c_out: int, bins: tuple[int, ...] = (1, 2, 4)) -> None:
        super().__init__()
        inter = max(c_in // 4, 16)
        self.bins = tuple(int(max(b, 1)) for b in bins)
        self.stages = nn.ModuleList(
            [
                nn.Sequential(
                    nn.AdaptiveAvgPool2d(b),
                    nn.Conv2d(c_in, inter, kernel_size=1, bias=False),
                    nn.BatchNorm2d(inter),
                    nn.ReLU(inplace=True),
                )
                for b in self.bins
            ]
        )
        self.fuse = nn.Sequential(
            nn.Conv2d(c_in + inter * len(self.bins), c_out, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(c_out),
            nn.ReLU(inplace=True),
            SEBlock(c_out),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h, w = x.shape[-2:]
        feats = [x]
        for stage in self.stages:
            y = stage(x)
            y = F.interpolate(y, size=(h, w), mode="bilinear", align_corners=False)
            feats.append(y)
        return self.fuse(torch.cat(feats, dim=1))


class SmallUNet(nn.Module):
    def __init__(
        self,
        in_channels: int = 10,
        out_channels: int = 24,
        base: int = 64,
        output_activation: OutputActivation = "softplus",
    ) -> None:
        super().__init__()
        self.inc = ConvBlock(in_channels, base, use_se=True)
        self.down1 = nn.Sequential(nn.MaxPool2d(2), ConvBlock(base, base * 2, use_se=True))
        self.down2 = nn.Sequential(nn.MaxPool2d(2), ConvBlock(base * 2, base * 4, use_se=True))
        self.down3 = nn.Sequential(nn.MaxPool2d(2), ConvBlock(base * 4, base * 8, use_se=True))
        self.context_dilated = ConvBlock(base * 8, base * 8, use_se=True, dilation=2)
        self.context_ppm = PyramidPooling(base * 8, base * 8, bins=(1, 2, 4))

        self.up1_conv = ConvBlock(base * 8 + base * 4, base * 4, use_se=True)
        self.up2_conv = ConvBlock(base * 4 + base * 2, base * 2, use_se=True)
        self.up3_conv = ConvBlock(base * 2 + base, base, use_se=True)
        self.out = nn.Conv2d(base, out_channels, kernel_size=1)

        act = str(output_activation).lower()
        if act not in {"softplus", "identity"}:
            raise ValueError(f"Unsupported output_activation: {output_activation}")
        self.output_activation = cast(OutputActivation, act)
        self.softplus = nn.Softplus(beta=1.0)

    def _apply_output_activation(self, x: torch.Tensor) -> torch.Tensor:
        if self.output_activation == "softplus":
            return self.softplus(x)
        if self.output_activation == "identity":
            return x
        raise ValueError(f"Unsupported output_activation: {self.output_activation}")

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)
        x4 = self.context_dilated(x4)
        x4 = self.context_ppm(x4)

        x = F.interpolate(x4, size=x3.shape[-2:], mode="bilinear", align_corners=False)
        x = torch.cat([x, x3], dim=1)
        x = self.up1_conv(x)

        x = F.interpolate(x, size=x2.shape[-2:], mode="bilinear", align_corners=False)
        x = torch.cat([x, x2], dim=1)
        x = self.up2_conv(x)

        x = F.interpolate(x, size=x1.shape[-2:], mode="bilinear", align_corners=False)
        x = torch.cat([x, x1], dim=1)
        x = self.up3_conv(x)

        x = self.out(x)
        return self._apply_output_activation(x)


class CostPropagationRefiner(nn.Module):
    def __init__(self, channels: int, steps: int = 4) -> None:
        super().__init__()
        self.channels = int(max(channels, 1))
        self.steps = int(max(steps, 1))
        self.depthwise = nn.Conv2d(
            self.channels,
            self.channels,
            kernel_size=3,
            padding=1,
            groups=self.channels,
            bias=False,
        )
        with torch.no_grad():
            # 8-neighborhood averaging kernel (center excluded).
            k = torch.tensor(
                [
                    [1.0 / 8.0, 1.0 / 8.0, 1.0 / 8.0],
                    [1.0 / 8.0, 0.0, 1.0 / 8.0],
                    [1.0 / 8.0, 1.0 / 8.0, 1.0 / 8.0],
                ],
                dtype=torch.float32,
            )
            w = k.view(1, 1, 3, 3).repeat(self.channels, 1, 1, 1)
            self.depthwise.weight.copy_(w)

        self.state_gate = nn.Sequential(
            nn.Conv2d(self.channels + 2, self.channels, kernel_size=1, bias=True),
            nn.Sigmoid(),
        )
        self.step_logits = nn.Parameter(torch.full((self.steps, self.channels, 1, 1), -1.2))

    def forward(self, y: torch.Tensor, occ: torch.Tensor, esdf_norm: torch.Tensor) -> torch.Tensor:
        if y.ndim != 4:
            return y
        free = (occ < 0.5).to(y.dtype)
        z = y
        for i in range(self.steps):
            nbr = self.depthwise(z)
            gate = self.state_gate(torch.cat([z, occ, esdf_norm], dim=1))
            step = torch.sigmoid(self.step_logits[i]).to(y.dtype)
            # In cluttered low-clearance regions keep updates conservative.
            clearance_scale = 0.4 + 0.6 * esdf_norm
            update = (nbr - z) * gate * clearance_scale
            z = z + step * update * free
        return z


class SmallUNetPropagation(nn.Module):
    def __init__(
        self,
        in_channels: int = 10,
        out_channels: int = 24,
        base: int = 64,
        output_activation: OutputActivation = "softplus",
        propagation_steps: int = 4,
    ) -> None:
        super().__init__()
        self.inc = ConvBlock(in_channels, base, use_se=True)
        self.down1 = nn.Sequential(nn.MaxPool2d(2), ConvBlock(base, base * 2, use_se=True))
        self.down2 = nn.Sequential(nn.MaxPool2d(2), ConvBlock(base * 2, base * 4, use_se=True))
        self.down3 = nn.Sequential(nn.MaxPool2d(2), ConvBlock(base * 4, base * 8, use_se=True))
        self.context_dilated = ConvBlock(base * 8, base * 8, use_se=True, dilation=2)
        self.context_ppm = PyramidPooling(base * 8, base * 8, bins=(1, 2, 4))

        self.up1_conv = ConvBlock(base * 8 + base * 4, base * 4, use_se=True)
        self.up2_conv = ConvBlock(base * 4 + base * 2, base * 2, use_se=True)
        self.up3_conv = ConvBlock(base * 2 + base, base, use_se=True)
        self.out = nn.Conv2d(base, out_channels, kernel_size=1)
        self.refiner = CostPropagationRefiner(channels=out_channels, steps=propagation_steps)

        act = str(output_activation).lower()
        if act not in {"softplus", "identity"}:
            raise ValueError(f"Unsupported output_activation: {output_activation}")
        self.output_activation = cast(OutputActivation, act)
        self.softplus = nn.Softplus(beta=1.0)

    def _apply_output_activation(self, x: torch.Tensor) -> torch.Tensor:
        if self.output_activation == "softplus":
            return self.softplus(x)
        if self.output_activation == "identity":
            return x
        raise ValueError(f"Unsupported output_activation: {self.output_activation}")

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)
        x4 = self.context_dilated(x4)
        x4 = self.context_ppm(x4)

        y = F.interpolate(x4, size=x3.shape[-2:], mode="bilinear", align_corners=False)
        y = torch.cat([y, x3], dim=1)
        y = self.up1_conv(y)

        y = F.interpolate(y, size=x2.shape[-2:], mode="bilinear", align_corners=False)
        y = torch.cat([y, x2], dim=1)
        y = self.up2_conv(y)

        y = F.interpolate(y, size=x1.shape[-2:], mode="bilinear", align_corners=False)
        y = torch.cat([y, x1], dim=1)
        y = self.up3_conv(y)

        y = self.out(y)
        occ = x[:, 0:1]
        esdf_norm = x[:, 1:2] if x.shape[1] >= 2 else torch.ones_like(occ)
        y = self.refiner(y, occ=occ, esdf_norm=esdf_norm)
        return self._apply_output_activation(y)


class SmallUNetLegacy(nn.Module):
    def __init__(
        self,
        in_channels: int = 10,
        out_channels: int = 24,
        base: int = 64,
        output_activation: OutputActivation = "softplus",
    ) -> None:
        super().__init__()
        self.inc = ConvBlock(in_channels, base, use_se=True)
        self.down1 = nn.Sequential(nn.MaxPool2d(2), ConvBlock(base, base * 2, use_se=True))
        self.down2 = nn.Sequential(nn.MaxPool2d(2), ConvBlock(base * 2, base * 4, use_se=True))
        self.down3 = nn.Sequential(nn.MaxPool2d(2), ConvBlock(base * 4, base * 8, use_se=True))

        self.up1_conv = ConvBlock(base * 8 + base * 4, base * 4, use_se=True)
        self.up2_conv = ConvBlock(base * 4 + base * 2, base * 2, use_se=True)
        self.up3_conv = ConvBlock(base * 2 + base, base, use_se=True)
        self.out = nn.Conv2d(base, out_channels, kernel_size=1)

        act = str(output_activation).lower()
        if act not in {"softplus", "identity"}:
            raise ValueError(f"Unsupported output_activation: {output_activation}")
        self.output_activation = cast(OutputActivation, act)
        self.softplus = nn.Softplus(beta=1.0)

    def _apply_output_activation(self, x: torch.Tensor) -> torch.Tensor:
        if self.output_activation == "softplus":
            return self.softplus(x)
        if self.output_activation == "identity":
            return x
        raise ValueError(f"Unsupported output_activation: {self.output_activation}")

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)

        x = F.interpolate(x4, size=x3.shape[-2:], mode="bilinear", align_corners=False)
        x = torch.cat([x, x3], dim=1)
        x = self.up1_conv(x)

        x = F.interpolate(x, size=x2.shape[-2:], mode="bilinear", align_corners=False)
        x = torch.cat([x, x2], dim=1)
        x = self.up2_conv(x)

        x = F.interpolate(x, size=x1.shape[-2:], mode="bilinear", align_corners=False)
        x = torch.cat([x, x1], dim=1)
        x = self.up3_conv(x)

        x = self.out(x)
        return self._apply_output_activation(x)


def build_model(
    model_name: str,
    in_channels: int,
    out_channels: int,
    base: int,
    output_activation: OutputActivation | str,
) -> nn.Module:
    name = str(model_name).lower()
    if name in {"tinyunet", "tiny_unet", "tiny"}:
        return TinyUNet(
            in_channels=in_channels,
            out_channels=out_channels,
            base=base,
            output_activation=cast(OutputActivation, str(output_activation).lower()),
        )
    if name in {"smallunet", "small_unet", "small"}:
        return SmallUNet(
            in_channels=in_channels,
            out_channels=out_channels,
            base=base,
            output_activation=cast(OutputActivation, str(output_activation).lower()),
        )
    if name in {"smallunet_prop", "small_unet_prop", "smallunet_propagation", "small_propagation"}:
        return SmallUNetPropagation(
            in_channels=in_channels,
            out_channels=out_channels,
            base=base,
            output_activation=cast(OutputActivation, str(output_activation).lower()),
            propagation_steps=4,
        )
    if name in {"smallunet_legacy", "small_unet_legacy", "small_legacy", "smallunet_v1"}:
        return SmallUNetLegacy(
            in_channels=in_channels,
            out_channels=out_channels,
            base=base,
            output_activation=cast(OutputActivation, str(output_activation).lower()),
        )
    raise ValueError(f"Unsupported model_name: {model_name}")
