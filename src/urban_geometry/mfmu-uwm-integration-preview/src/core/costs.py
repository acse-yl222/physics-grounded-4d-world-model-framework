"""cost function 台账 —— 核心保持简单:2 个必选 + 2 个可选,一项一节,eq 编号对齐论文。

必选(= 正典数学,一字不动;bitwise gate 卡住):
  TravelCost   eq53   f_tbc = D.T @ x_{k-1} + D @ x_{k+1}(终端 Neumann 复制,§3.11)
  CapacityCost eq55   f_cap = λ_cap[k] · (occ − C_cap[k]) · (1−s[i,k]),occ = Σ_j (1−s)x(eq25)

可选(实验记录见 backup/labs/eps_tiebreak_lab.py 台账,2026-07-19):
  TieBreakCost(ε)  时间偏好:第 j 段边价 ×(1+ε·j)(j=0 出生段中性)。确定性解除时机并列;
                   与 γs(eq22)同占边价倍率槽位,可表述为 eq22 同族。⚠ 必须与 longhop
                   同开(否则瞬移被抬成严格最优 —— 已验证的处方)。
  ConcCost(μ)      Potts 双阱 F += μ·Σx(1−x):cost(one-hot) < cost(0.5/0.5)。小 λ 场景
                   的时机并列可用;归属并列有相变悬崖、fullscale 不迁移 —— 默认关。

crisp 能量评审一律走冻结层 compute_F(单一事实源),本模块不重复实现。
"""
from dataclasses import dataclass

from ._frozen import compute_F


@dataclass(frozen=True)
class CostConfig:
    """求解器的力场配置。默认值 = 正典 s=0 行为(全部可选项关闭)。"""
    eps_time: float = 0.0        # TieBreakCost 强度(0=关;开则捆绑 scenario.longhop)
    mu_conc: float = 0.0         # ConcCost 强度(0=关;默认关,见台账)

    def describe(self):
        parts = ["TravelCost(eq53)", "CapacityCost(eq55)"]
        if self.eps_time:
            parts.append(f"TieBreakCost(ε={self.eps_time:g})")
        if self.mu_conc:
            parts.append(f"ConcCost(μ={self.mu_conc:g})")
        return " + ".join(parts)


def crisp_energy(x_crisp, D, Ccap, lam_cap):
    """crisp 解的原始 F(口径:ε/μ 只引导求解,评审永远用原始 F)。"""
    return float(compute_F(x_crisp, D, Ccap, lam_cap)["F_total"])
