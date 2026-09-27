"""CNNJacobiSolver —— eq53/eq55 力场的 CNN 表达 + 全并行 red-black 退火求解。

【CNN 主引擎 V1,CD_MINIMAL_PROTOCOL】donor e7884e0 适配版。与 donor 的差异
(卡 §四.4 逐条):
  - 全部合同检查用显式 ValueError/RuntimeError(不用 assert —— `python -O` 下
    assert 会被剥除,负控 D 组要求两种模式下均 fail-closed);
  - device 必须显式提供;请求 CUDA 但 CUDA 不可用立即 RuntimeError;
    禁止任何静默 CUDA→CPU fallback;
  - 正式路径只接受 FP64(dtype="float64");
  - measure_theta_c 增加 chunk 参数(BoHan DS-1 批复):只改变 batch 分块方式,
    15 个 θ 点、seed、顺序、阈值 (1/M+1)/2 与线性插值公式与原口径完全相同;
  - 不修改正典 solver(src/core/scheduler.py 零改动)。

数学口径:力场公式逐项照抄 scheduler.py jacobi 分支(eq53 + eq55 [+ ε / μ]),
softmax(eq72)+ 欠松弛 α、退火台阶(eq73)、停机判据与 MeanFieldScheduler 同构。
update="redblack"(奇/偶时间片两拍;二分图着色)为唯一模式。
轨迹与正典必然不同;验收走 experiments/ai4pde_main_engine.py 的算子/决策 gate。
"""
import numpy as np
import torch
import torch.nn as nn

from src.core.costs import CostConfig
from src.core.result import Result

from .kernels import TravelKernel1D

# θ 日程口径(单一源;runner 与 gate 从这里取)
THETA0_FRAC = 0.95
THETA_MIN_FRAC = 0.02


def _require_fp64(dtype):
    if dtype != "float64":
        raise ValueError(
            f"CNN 主引擎正式合同只接受 dtype='float64',收到 {dtype!r}(FP32 属探索口径,本线排除)")
    return torch.float64


def _require_device(device):
    if device is None:
        raise ValueError("CNN 主引擎正式合同要求显式 device(如 'cuda');不提供即拒绝,不做自动探测")
    dev = str(device)
    if dev.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError(
            f"请求 device={dev!r} 但 CUDA 不可用;正式合同禁止静默 CUDA→CPU fallback,立即拒绝")
    return device


class CNNJacobiField(nn.Module):
    """力场 f(x) 的一次前向 = 对全部 k 同时求值(冻结当前 x 的快照)。

    f = conv_km1(x) + conv_kp1(x)                       eq53(ε 变体见下)
      + λ[k]·(occ − C_cap[k])·(1−s)                     eq55,occ 全架共享快照
      [+ μ·(1−2x)]                                      ConcCost(默认关)
    ε≠0:  f = c_prev[k]·conv_km1(x) + c_next[k]·conv_kp1(x)(TieBreak 边价倍率)
    γs(eq22 amp 场)不在本线合同内:kwarg 位保留(planner 构造点无条件传参),
    非零立即 ValueError。
    """

    def __init__(self, D, Ccap, lam_cap, s, *, gamma_s=0.0, eps=0.0, mu=0.0,
                 dtype="float64", device=None):
        super().__init__()
        if float(gamma_s) != 0.0:
            raise ValueError(
                f"CNN 主引擎正式合同要求 gamma_s=0(eq22 hold 走冻结正典),收到 {gamma_s!r}")
        td = _require_fp64(dtype)
        device = _require_device(device)
        self.device = device
        K = np.asarray(Ccap).shape[0]
        self.eps, self.mu = float(eps), float(mu)
        self.km1 = TravelKernel1D("km1", D, dtype=td)
        self.kp1 = TravelKernel1D("kp1", D, dtype=td)
        reg = lambda name, arr: self.register_buffer(
            name, torch.tensor(np.asarray(arr, float), dtype=td))
        reg("lam", lam_cap)                               # (K,M)
        reg("Cc", Ccap)                                   # (K,M)
        reg("oms", 1.0 - np.asarray(s, float))            # (N,K,M) 1−s
        ks = np.arange(K)
        reg("cprev", 1.0 + self.eps * (ks - 1))           # (K,) k=0 处不被使用
        reg("cnext", 1.0 + self.eps * np.minimum(ks, K - 2))
        self.to(device)
        for p in self.parameters():                       # AI4PDEs 约定:权重冻结
            p.requires_grad_(False)

    def _dirconv(self, kern, x):
        """(B,N,K,M) → 方向卷积 → (B,N,K,M)。pad:左 0(k=0 场不被使用),
        右复制(终端 Neumann,§3.11:xkn(K-1) = x[K-1])。"""
        B, N, K, M = x.shape
        xc = x.reshape(B * N, K, M).transpose(1, 2)       # (BN, M, K)
        xp = torch.cat([xc.new_zeros(B * N, M, 1), xc, xc[:, :, -1:]], dim=2)
        return kern(xp).transpose(1, 2).reshape(B, N, K, M)

    def forward(self, x):
        B, N, K, M = x.shape
        if self.eps != 0.0:                               # TieBreak(ε)
            f = self.cprev.view(1, 1, K, 1) * self._dirconv(self.km1, x) \
                + self.cnext.view(1, 1, K, 1) * self._dirconv(self.kp1, x)
        else:                                             # TravelCost(eq53)
            f = self._dirconv(self.km1, x) + self._dirconv(self.kp1, x)
        occ = torch.einsum("nkm,bnkm->bkm", self.oms, x)  # 全架共享占用快照
        f = f + self.lam.view(1, 1, K, -1) \
            * (occ.unsqueeze(1) - self.Cc.view(1, 1, K, -1)) * self.oms.unsqueeze(0)
        if self.mu != 0.0:                                # ConcCost(默认关)
            f = f + self.mu * (1.0 - 2.0 * x)
        return f


class CNNJacobiSolver:
    """用法(接口对齐 MeanFieldScheduler 子集;返回标准 Result,audit 直接可用):
        sol = CNNJacobiSolver(D, Ccap, lam_cap, x0s, device="cuda")
        res = sol.solve(seeds=range(5), theta0=..., theta_min=...)
    """

    def __init__(self, D, Ccap, lam_cap, x0s, *, s=None, pins=None, gamma_s=0.0,
                 costs=None, update="redblack", dtype="float64", device=None):
        if update != "redblack":
            raise ValueError(
                f"CNN 主引擎正式合同 inner sweep 仅 'redblack',收到 {update!r}(sync 已出场景)")
        self._td = _require_fp64(dtype)
        device = _require_device(device)
        self.update = update
        self.dtype = dtype
        self.D = np.asarray(D, float)
        self.Ccap = np.asarray(Ccap, float)
        self.lam_cap = np.asarray(lam_cap, float)
        self.x0s = np.asarray(x0s, float)
        self.N, self.M = self.x0s.shape
        self.K = self.Ccap.shape[0]
        self.costs = costs or CostConfig()
        self.s = np.zeros((self.N, self.K, self.M)) if s is None \
            else np.broadcast_to(np.asarray(s, float), (self.N, self.K, self.M)).copy()
        self.pins = dict(pins or {})
        self.field = CNNJacobiField(self.D, self.Ccap, self.lam_cap, self.s,
                                    gamma_s=gamma_s, eps=self.costs.eps_time,
                                    mu=self.costs.mu_conc, dtype=dtype, device=device)
        self.device = self.field.device
        self._theta_c = None

        upd = np.ones((self.N, self.K), dtype=bool)
        upd[:, 0] = False                                 # k=0 = 出生层,永不更新
        for (pi, pk) in self.pins:
            upd[pi, pk] = False
        self.updmask = torch.tensor(upd, device=self.device)
        ks = torch.arange(self.K, device=self.device)
        self.colors = [ks % 2 == 1, (ks % 2 == 0) & (ks > 0)]   # redblack 奇/偶两拍

    # ---------------- θc:批量 ladder 测量(语义 = 正典 measure_theta_c 移植) ----------------
    def measure_theta_c(self, n=15, seed=0, tol=1e-9, chunk=None):
        """FP64 ladder 自测。chunk(DS-1):None = 单批 B=n(原口径);int c = 按
        c 个 θ 点一组分块顺序求解,仅改变 batch 组装方式 —— θ 点(geomspace)、
        seed、顺序、饱和度阈值 (1/M+1)/2 与线性插值公式与原口径完全相同;
        不修改 src/core/scheduler.py。分块与非分块的一致性由
        ai4pde_main_engine --ladder-align 在小型 fixture 上以预注册容差先行验证。"""
        from src.core._frozen import theta_c_scalar_multi
        thresh = (1.0 / self.M + 1.0) / 2.0
        tcs = theta_c_scalar_multi(self.D, self.Ccap, self.lam_cap, self.N)
        ladder = np.geomspace(3.0 * tcs, 0.005 * tcs, n)
        sizes = [n] if not chunk else \
            [min(chunk, n - i) for i in range(0, n, chunk)]
        mp_parts, pos = [], 0
        for b in sizes:
            rungs = ladder[pos:pos + b]
            res = self.solve(theta0=rungs, theta_min=rungs, seeds=[seed] * b,
                             gamma=1.0, max_inner=3000, tol=tol)
            mp_parts.append(res.x[:, :, 1:, :].max(3).reshape(b, -1).mean(1))
            pos += b
        mp = np.concatenate(mp_parts)
        for j in range(1, n):
            if (mp[j - 1] - thresh) * (mp[j] - thresh) < 0:
                t0, y0, t1, y1 = ladder[j - 1], mp[j - 1], ladder[j], mp[j]
                return float(t0 + (thresh - y0) * (t1 - t0) / (y1 - y0))
        return float(ladder[-1])

    def measure_theta_c_full(self, n=15, seed=0, tol=1e-9, chunk=None):
        """--ladder-align 用:返回 (theta_c, ladder, 饱和度曲线) 供两种分块方式留档对比。"""
        from src.core._frozen import theta_c_scalar_multi
        thresh = (1.0 / self.M + 1.0) / 2.0
        tcs = theta_c_scalar_multi(self.D, self.Ccap, self.lam_cap, self.N)
        ladder = np.geomspace(3.0 * tcs, 0.005 * tcs, n)
        sizes = [n] if not chunk else \
            [min(chunk, n - i) for i in range(0, n, chunk)]
        mp_parts, pos = [], 0
        for b in sizes:
            rungs = ladder[pos:pos + b]
            res = self.solve(theta0=rungs, theta_min=rungs, seeds=[seed] * b,
                             gamma=1.0, max_inner=3000, tol=tol)
            mp_parts.append(res.x[:, :, 1:, :].max(3).reshape(b, -1).mean(1))
            pos += b
        mp = np.concatenate(mp_parts)
        tc = float(ladder[-1])
        for j in range(1, n):
            if (mp[j - 1] - thresh) * (mp[j] - thresh) < 0:
                t0, y0, t1, y1 = ladder[j - 1], mp[j - 1], ladder[j], mp[j]
                tc = float(t0 + (thresh - y0) * (t1 - t0) / (y1 - y0))
                break
        return tc, ladder, mp

    # ---------------- θc:委托正典测量(单一事实源;numba 快路径,失败退 numpy) ----------------
    @property
    def theta_c(self):
        if self._theta_c is None:
            from src.core.scheduler import MeanFieldScheduler
            last_err = None
            for bk in ("numba", "numpy"):
                try:
                    self._theta_c = MeanFieldScheduler(
                        self.D, self.Ccap, self.lam_cap, self.x0s, backend=bk,
                        s=self.s, pins=self.pins).theta_c
                    break
                except Exception as e:                    # noqa: BLE001 后端缺失时按序回退
                    last_err = e
            if self._theta_c is None:
                raise RuntimeError(f"θc 委托测量失败(numba 与 numpy 均不可用):{last_err}")
        return self._theta_c

    # ---------------- 求解(循环结构同构 MeanFieldScheduler.solve) ----------------
    @torch.no_grad()
    def solve(self, *, seeds=(0,), theta0=None, theta_min=None, gamma=0.95, alpha=0.1,
              tol=1e-9, max_inner=300, max_outer=400, sat_stop=0.95, x_init=None):
        N, K, M = self.N, self.K, self.M
        if theta0 is None or theta_min is None:
            raise ValueError("CNN 主引擎正式合同要求显式 theta0/theta_min(缺省会触发不可负担的冻结 θc 测量)")

        # 初值:CPU 上逐 seed default_rng(与正典逐位同源),再整体搬 device
        if x_init is not None:
            x_np = np.array(x_init, float)
            B = x_np.shape[0]
            seeds = list(seeds)[:B] if seeds else list(range(B))
        else:
            seeds = list(seeds)
            B = len(seeds)
            x_np = np.empty((B, N, K, M))
            for b, sd in enumerate(seeds):
                rng = np.random.default_rng(sd)
                xb = rng.uniform(0.9, 1.1, (N, K, M))
                xb[:, 1:, :] /= xb[:, 1:, :].sum(2, keepdims=True)
                x_np[b] = xb
        x_np[:, :, 0, :] = self.x0s[None]
        for (pi, pk), pmu in self.pins.items():
            x_np[:, pi, pk, :] = 0.0
            x_np[:, pi, pk, pmu] = 1.0

        dev, td = self.device, self._td
        x = torch.tensor(x_np, dtype=td, device=dev)
        theta = torch.tensor(np.broadcast_to(np.asarray(theta0, float), (B,)).copy(),
                             dtype=td, device=dev)
        th_min = torch.tensor(np.broadcast_to(np.asarray(theta_min, float), (B,)).copy(),
                              dtype=td, device=dev)
        dx_last = torch.ones(B, dtype=td, device=dev)
        done = torch.zeros(B, dtype=torch.bool, device=dev)

        for _outer in range(max_outer):
            inner_done = done.clone()
            for _inner in range(max_inner):
                active = ~inner_done
                if not bool(active.any()):
                    break
                xo = x.clone()
                for cmask in self.colors:                 # redblack:奇/偶两拍
                    f = self.field(x)
                    z = -f / theta.view(B, 1, 1, 1)
                    z = z - z.amax(3, keepdim=True)
                    e = z.exp()
                    xin = (1 - alpha) * x + alpha * (e / e.sum(3, keepdim=True))
                    cond = active.view(B, 1, 1, 1) \
                        & self.updmask.view(1, N, K, 1) & cmask.view(1, 1, K, 1)
                    x = torch.where(cond, xin, x)         # softmax(eq72)+ 欠松弛
                dxb = (x - xo).abs().reshape(B, -1).amax(1)
                dx_last = torch.where(active, dxb, dx_last)
                inner_done = inner_done | (active & (dxb < tol))
            sat = x[:, :, 1:, :].amax(3).reshape(B, -1).mean(1) >= sat_stop
            newly = (~done) & (((dx_last < tol) & sat) | (theta <= th_min * (1 + 1e-12)))
            done = done | newly
            if bool(done.all()):
                break
            theta = torch.where(done, theta, torch.maximum(theta * gamma, th_min))  # eq73
        res = Result(x=x.double().cpu().numpy().copy(),
                     dx=dx_last.double().cpu().numpy().copy(), seeds=list(seeds))
        res.params = dict(backend="ai4pde-cnn-main-v1", device=str(dev), update=self.update,
                          dtype=self.dtype, costs=self.costs.describe(),
                          gamma=gamma, alpha=alpha, tol=tol,
                          max_inner=max_inner, max_outer=max_outer, sat_stop=sat_stop,
                          seeds=list(seeds))
        return res
