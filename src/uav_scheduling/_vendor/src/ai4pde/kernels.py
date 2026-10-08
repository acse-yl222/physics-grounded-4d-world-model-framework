"""TravelKernel1D —— eq53 旅行力场的时间轴 Conv1d 表达(冻结权重,无训练)。

【CNN 主引擎 V1,CD_MINIMAL_PROTOCOL】donor e7884e0 选择性移植:仅 TravelKernel1D;
MG 转移核(Prolong/Restrict/_prolong_idx)按卡 §四.3 明确不移植。

结构:nn.Conv1d(M, M, kernel_size=3, bias=False),M 站点 = M 通道,
D 矩阵 = 通道混合权重;'km1' 方向抽头 0 放 D.T,'kp1' 方向抽头 2 放 D;
输入须由调用方 pad 成 (B', M, K+2)(左 0 / 右复制,见 jacobi_cnn._dirconv)。
"""
import numpy as np
import torch
import torch.nn as nn


class TravelKernel1D(nn.Module):
    """eq53 的单方向旅行卷积核(权重冻结)。direction ∈ {'km1','kp1'}。"""

    def __init__(self, direction, D, dtype=torch.float64):
        super().__init__()
        if direction not in ("km1", "kp1"):
            raise ValueError(f"direction 仅接受 'km1'/'kp1',收到 {direction!r}")
        D = np.asarray(D, float)
        M = D.shape[0]
        w = np.zeros((M, M, 3))
        if direction == "km1":                            # f += x_{k-1} @ D
            w[:, :, 0] = D.T
        else:                                             # f += x_{k+1} @ D.T
            w[:, :, 2] = D
        conv = nn.Conv1d(M, M, kernel_size=3, bias=False)
        conv.weight = nn.Parameter(torch.tensor(w, dtype=dtype), requires_grad=False)
        self.conv = conv                                  # donor 原式:整体替换 Parameter,dtype 由构造决定

    def forward(self, x_padded):
        return self.conv(x_padded)
