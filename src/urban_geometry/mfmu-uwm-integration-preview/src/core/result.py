"""Result / TraceRecorder:实验输出的标准载体。

每次 solve 返回 Result;Result.save(run_dir) 落盘为标准 per-run 目录:
    params.json   完整参数快照(场景+solver+代码版本)
    metrics.json  审计结果(experiments.audit 填充)
    result.npz    最终解:x (B,N,K,M)、dx、crisp 轨迹、legs
    trace.npz     (开 trace 时)中间产物:θ/|dx| 全序列 + 每 stride 个 sweep 的 x 快照
Result.load(run_dir) 原样读回,供事后可视化/分析。
"""
import json
import os
from dataclasses import dataclass, field

import numpy as np


class TraceRecorder:
    """中间产物记录器:θ/|dx| 每 sweep 都记(便宜),x 快照每 stride 个 sweep 记一张。"""

    def __init__(self, stride=25):
        self.stride = int(stride)
        self.sweeps, self.thetas, self.dxs = [], [], []
        self.snap_sweeps, self.snaps = [], []

    def record(self, sweep, theta_np, dx_np, x_np):
        self.sweeps.append(sweep)
        self.thetas.append(theta_np.copy())
        self.dxs.append(dx_np.copy())
        if sweep % self.stride == 0:
            self.snap_sweeps.append(sweep)
            self.snaps.append(x_np.copy())

    def arrays(self):
        return dict(sweeps=np.asarray(self.sweeps),
                    thetas=np.stack(self.thetas) if self.thetas else np.zeros((0, 0)),
                    dxs=np.stack(self.dxs) if self.dxs else np.zeros((0, 0)),
                    snap_sweeps=np.asarray(self.snap_sweeps),
                    snaps=np.stack(self.snaps) if self.snaps else np.zeros((0,)))


@dataclass
class Result:
    x: np.ndarray                      # (B,N,K,M) 软解
    dx: np.ndarray                     # (B,) 末端 |dx|
    seeds: list
    params: dict = field(default_factory=dict)     # 场景+solver+版本快照
    metrics: dict = field(default_factory=dict)    # experiments.audit 填充
    legs: list = field(default_factory=list)       # 每 seed 的腿清单(transit 重建)
    trace: dict = field(default_factory=dict)      # TraceRecorder.arrays() 或空

    # ---------- 便捷读出 ----------
    def trajectories(self):
        """(B,N,K) 0-based argmax 轨迹。"""
        return self.x.argmax(3)

    def saturation(self):
        """(B,) 平均 max-prob(k≥2 层,正典口径)。"""
        return self.x[:, :, 1:, :].max(3).reshape(self.x.shape[0], -1).mean(1)

    def crisp(self, b):
        """seed b 的 one-hot 解(N,K,M),供 compute_F 评审。"""
        B, N, K, M = self.x.shape
        xc = np.zeros((N, K, M))
        tr = self.x[b].argmax(2)
        for i in range(N):
            xc[i, np.arange(K), tr[i]] = 1.0
        return xc

    def snapshot(self, sweep):
        """最接近 sweep 的中间 x 快照(需开 trace)。"""
        ss = self.trace.get("snap_sweeps")
        if ss is None or len(ss) == 0:
            raise ValueError("本次 run 未开 trace(--trace)")
        j = int(np.abs(np.asarray(ss) - sweep).argmin())
        return int(ss[j]), self.trace["snaps"][j]

    # ---------- 落盘 / 读回 ----------
    def save(self, run_dir):
        os.makedirs(run_dir, exist_ok=True)
        with open(os.path.join(run_dir, "params.json"), "w") as f:
            json.dump(self.params, f, indent=2, ensure_ascii=False, default=str)
        with open(os.path.join(run_dir, "metrics.json"), "w") as f:
            json.dump(self.metrics, f, indent=2, ensure_ascii=False, default=str)
        np.savez_compressed(os.path.join(run_dir, "result.npz"),
                            x=self.x, dx=self.dx, seeds=np.asarray(self.seeds),
                            trajs=self.trajectories(),
                            legs=np.asarray(json.dumps(self.legs)))
        if self.trace:
            np.savez_compressed(os.path.join(run_dir, "trace.npz"), **self.trace)
        return run_dir

    @classmethod
    def load(cls, run_dir):
        z = np.load(os.path.join(run_dir, "result.npz"), allow_pickle=False)
        params = metrics = {}
        p = os.path.join(run_dir, "params.json")
        if os.path.exists(p):
            params = json.load(open(p))
        m = os.path.join(run_dir, "metrics.json")
        if os.path.exists(m):
            metrics = json.load(open(m))
        trace = {}
        t = os.path.join(run_dir, "trace.npz")
        if os.path.exists(t):
            with np.load(t) as tz:
                trace = {k: tz[k] for k in tz.files}
        legs = json.loads(str(z["legs"]))
        return cls(x=z["x"], dx=z["dx"], seeds=list(z["seeds"]), params=params,
                   metrics=metrics, legs=legs, trace=trace)
