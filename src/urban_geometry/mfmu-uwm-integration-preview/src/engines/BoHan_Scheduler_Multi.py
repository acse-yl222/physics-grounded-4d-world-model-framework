"""
BoHan_Scheduler_Multi.py —— 多架(N≥2)纯 mean-field 调度引擎,【s=0 阶段】(建造顺序第 1 步)。

相对单架版(BoHan_Scheduler_Single)只有三处结构变化,数学一个字没动:
  1. x → (N,K,M);每架每层归一(eq13);每架自己的起点 k=1 Dirichlet 钉死(§3.11)。
  2. f_cap 用【全体占用】occ = Σ_j y_j(eq55 的 Σ_j;含自己=真梯度),力再乘各架自己的 (1−s_i)。
  3. GS 加 UAV 维:逐架顺序更新(= 6/30 B1 验证的防撞 nudge)+ 每架内部 forward-backward 时间扫。
     随机初值保留(物理破缺主张在它身上,GS 顺序只是算法性破缺)。

验收(本文件 __main__):
  A. S3@N=2(不可兼达 → 可兼达):单架时 gap=+2 不收敛(FAIL);加一架后两单应全接、0 撞、gap=0。
  B. S4@N=2(精确对称):两架同起点、两个对称投递 = 6/29-6/30 的"对称自指派"同款;
     应一架去 1、一架去 5;并跑 20 seeds 撞车率,和 yueyan_meanfield B3(200 seeds 0% 撞)口径对表。
  裁判 = N=2 向量化联合枚举(joint F = F_tbc(a)+F_tbc(b)+F_cap(occ_a+occ_b),精确)。

口径:
  - gap = crisp 联合 F − 枚举最优;解 ∈ 最优集(考虑两架身份)。
  - 撞车 = 某个 C_cap=1 的格子 crisp 占用 >C(两架挤同一单);漏单 = 占用 <C。
  - 饱和:tie-aware —— n_opt>1(存在时机并列 = S2 族零模)时只报数值不强制 0.95;n_opt=1 时强制。
    (待 BoHan 拍板的口径,先按推荐写;要严格判改 SAT_TIE_AWARE=False。)

用法:python3 BoHan_Scheduler_Multi.py   → 控制台审计 + BoHan_Scheduler_Multi_viz.png
"""
import itertools
import os
import numpy as np
import sys as _sys, os as _os                      # path bootstrap (folder reorg 2026-07-04)
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))   # BoHan_From_Scratch/
for _sub in ("engines", "validation", "labs"):
    _p = _os.path.join(_ROOT, _sub)
    _p in _sys.path or _sys.path.insert(0, _p)
OUT_DIR = _os.path.join(_ROOT, "output")                                  # all figures go here
from compute_F_energy import compute_F                   # (N,K,M) 版能量,单一事实源

SAT_TIE_AWARE = True                                     # 并列场景不强制饱和 0.95(推荐口径,可改)
SAT_REQ = 0.95 - 1e-9


# ---------------- 场景 ----------------
def build_multi(M, K, starts, deliveries, longhop=None):
    """starts: 每架的起点站(1-based);deliveries: [(k, 站)];longhop=(阈值,倍率) 可选长跳加价。"""
    pos = np.arange(1, M + 1, dtype=float)
    D = np.abs(pos[:, None] - pos[None, :])              # eq15/19(单位间距 = 单位时间)
    if longhop is not None:
        thr, fac = longhop
        D = np.where(D > thr, D * fac, D)
    colsum = D.sum(0)
    Ccap = np.zeros((K, M)); lam_cap = np.zeros((K, M))
    for k, mu in deliveries:                             # 投递:C_cap=1,λ=2·colsum(eq90;N 架同构时不变)
        Ccap[k - 1, mu - 1] = 1.0
        lam_cap[k - 1, mu - 1] = 2.0 * colsum[mu - 1]
    x0s = np.zeros((len(starts), M))
    for i, st in enumerate(starts):
        x0s[i, st - 1] = 1.0
    return D, Ccap, lam_cap, x0s


# ---------------- 多架 SCF 求解器(§4.2:每温收敛再降温,停机=收敛+饱和,θ_min 兜底) ----------------
def solve_multi(D, Ccap, lam_cap, x0s, theta0, theta_min, s=None, gamma=0.95, alpha=0.1, seed=0,
                tol=1e-9, max_inner=300, max_outer=400, sat_stop=0.95, pins=None, gamma_s=0.0,
                x_init=None, trace=None, order_rng=None, lam_commit=None,
                c_commit=None, lam_commit2=None, noise_rng=None):
    """x:(N,K,M)。s:(N,K,M) 或 None(=0,本阶段)。pins:{(i,k): 站0based} 钉层(s-journey 用)。
    gamma_s>0 = eq22 原教旨 hold(dest-indexed:进入 s=1 承诺格的边价 ×(1+γs);"λstay is a large
    number",§3.5)——用于和 pin(=γs→∞ 极限)做等价对照;默认 0 完全不影响现行为。
    trace: optional callback trace(x, theta, dx) called once per inner sweep AFTER dx is
      computed (small-lab T3 per-sweep recording). Default None => bit-identical behaviour.
    order_rng: optional np.random.Generator; if given, the UAV update order is re-shuffled
      every inner sweep (small-lab T3 order-nudge control). Default None => fixed order 0..N-1.
    lam_commit: journey-commitment spring (paper 0709 eq31/32, three-way sign-off 2026-07-09).
      Scalar or (M,) per-column vector (our prescription: 2*colsum[mu]*lam_scale = the
      destination station's own lam_cap; valid because both s builders write windows only in
      the destination column and eq90's lambda is k-independent). Gates use the PREVIOUS
      layer's s (eq31 sums k=1..K-1); at the top row the forward difference vanishes via the
      same xn clamp as f_tbc (energetically exact). Default None => bit-identical behaviour.
    c_commit/lam_commit2: eq33 soft pin (paper 0709 §3.7.2, T13 three-way sign-off 2026-07-10).
      c_commit: (N,K,M) committed-target field, one-hot on committed rows, all-zero rows
      elsewhere. Force f += lam_commit2 * c * (x - c) -- gated by c ITSELF, not by our s
      field: paper eq33's s is the flight-commitment indicator, while our s is overloaded
      with feasibility masks (c-gating = the faithful eq33 semantics, keeps engineering
      masks out of the paper term). lam_commit2: scalar or (M,). Default None => off.
    noise_rng: eq110 noise term (paper 0709 §5.5; T16 three-way sign-off 2026-07-12).
      np.random.Generator or None. When active, each unpinned row update adds the
      Euler-Maruyama discretisation of eq110's sqrt(T)*xi: sqrt(alpha*theta)*N(0,1)
      per cell (amplitude FIXED by the paper + dt=alpha; anneals with theta
      automatically), then clip>=0 + row renormalise (signed F3; the simplex is our
      discrete eq13 constraint). iid per (i,k,mu) (signed F2). Pinned/birth rows never
      touched. Keep this rng SEPARATE from the init seed (reproducibility ledger).
      Default None => bit-identical behaviour. NOTE: eq110's diffusion term D-nabla^2
      (diffusion coefficient D, NOT our distance matrix D) is deliberately NOT
      implemented here (signed m2: noise term only).
    返回 (x, 最终|dx|)。"""
    N, M = x0s.shape
    K = Ccap.shape[0]
    s = np.zeros((N, K, M)) if s is None else np.broadcast_to(np.asarray(s, float), (N, K, M)).copy()
    pins = pins or {}
    if x_init is not None:
        x = np.array(x_init, float)                      # 断点续跑:接上一段的 x(分块退火用)
    else:
        rng = np.random.default_rng(seed)
        x = rng.uniform(0.9, 1.1, (N, K, M))             # 随机初值 = 物理破缺 nudge
        x[:, 1:, :] /= x[:, 1:, :].sum(2, keepdims=True) # 每架每层归一(eq13)
    x[:, 0, :] = x0s                                     # 各架起点 Dirichlet
    for (pi, pk), pmu in pins.items():
        x[pi, pk] = 0.0; x[pi, pk, pmu] = 1.0
    theta = theta0

    def upd(i, k):                                       # 一次 GS 更新(用当前 x:邻层/别架已更新)
        xp = x[i, k - 1]
        xn = x[i, k + 1] if k + 1 <= K - 1 else x[i, K - 1]   # 终端 Neumann 复制(§3.11)
        if gamma_s > 0.0:                                # eq22 hold(source-indexed,§3.5 意图:
            xp_amp = (1.0 + gamma_s * s[i, k - 1]) * xp  #  "deters changing from the previous level"
            f_tbc = D.T @ xp_amp + (1.0 + gamma_s * s[i, k]) * (D @ xn)   # 离开承诺格的边 ×(1+γs)
            # ⚠️ 发现:eq22 按字面是 dest-indexed(进入 s=1 格的边加价)——那会把旅程的出发边
            #    (起点→承诺格,恰落在首个 s=1 层)打成天价,旅程无法开始;按 §3.5 意图应为
            #    source-indexed(离开承诺格加价)。呼应 6/9 demo 的 source-indexed 记录。可报 Chris。
        else:
            f_tbc = D.T @ xp + D @ xn                    # eq53(gamma_s=0 → 原样)
        occ = ((1.0 - s[:, k, :]) * x[:, k, :]).sum(0)   # Σ_j y_j(eq25/eq55;含自己=真梯度)
        f = f_tbc + lam_cap[k] * (occ - Ccap[k]) * (1.0 - s[i, k])   # eq53 + eq55
        if lam_commit is not None:                       # eq32 journey spring(0709;不带 (1−s) 门控,eq75)
            f = f + lam_commit * (s[i, k - 1] * (x[i, k] - xp) - s[i, k] * (xn - x[i, k]))
        if c_commit is not None:                         # eq33 soft pin(0709 §3.7.2;c-gated,见 docstring)
            f = f + lam_commit2 * c_commit[i, k] * (x[i, k] - c_commit[i, k])
        z = -f / theta; z -= z.max()
        e = np.exp(z)
        x[i, k] = (1 - alpha) * x[i, k] + alpha * (e / e.sum())   # softmax(eq72)+ 欠松弛
        if noise_rng is not None:                        # eq110 噪声项(EM 离散,√(αθ)·ξ)
            row = x[i, k] + np.sqrt(alpha * theta) * noise_rng.standard_normal(x.shape[2])
            np.maximum(row, 0.0, out=row)
            ssum = row.sum()
            if ssum > 0.0:
                x[i, k] = row / ssum                     # clip + 重归一(F3,eq13 约束)

    dx = 1.0
    for _ in range(max_outer):                           # 外层 = 一个固定温度(§4.2)
        for _ in range(max_inner):                       # 内层 = 该温度迭代到收敛
            xo = x.copy()
            uav_order = order_rng.permutation(N) if order_rng is not None else range(N)
            for i in uav_order:                          # ★ GS-over-UAV:逐架顺序(防撞 nudge)
                for k in range(1, K):                    #   ① forward
                    if (i, k) not in pins:
                        upd(i, k)
                for k in range(K - 1, 0, -1):            #   ② backward(Chris 的 fb-GS)
                    if (i, k) not in pins:
                        upd(i, k)
            dx = float(np.abs(x - xo).max())
            if trace is not None:
                trace(x, theta, dx)
            if dx < tol:
                break
        saturated = float(x[:, 1:, :].max(2).mean()) >= sat_stop
        if (dx < tol and saturated) or theta <= theta_min * (1 + 1e-12):
            break
        theta = max(theta * gamma, theta_min)            # 退火(eq73)
    return x, dx


# ---------------- θc:标量参考(定扫描范围)+ 实测(定退火起点) ----------------
def theta_c_scalar_multi(D, Ccap, lam_cap, N):
    """eq86 按 eq91 平均;注意 λ 项是 Σ_{j=1..N} → 全可用(s=0)时 ×N。只用来定扫描范围。"""
    M = Ccap.shape[1]
    colsum = D.sum(0)
    return float((((2.0 * colsum)[None, :] + N * lam_cap) / M).mean())


def measure_theta_c_multi(D, Ccap, lam_cap, x0s, n=15, seed=0, s=None, lam_commit=None):
    """s/lam_commit: opt-in (T12 sign-off ⑤) —— 带弹簧的臂用自己的力场实测 θc;
    默认 None = 无 s 基线,与历史缓存口径完全一致。"""
    N, M = x0s.shape
    thresh = (1.0 / M + 1.0) / 2.0
    tcs = theta_c_scalar_multi(D, Ccap, lam_cap, N)
    prev = None
    for th in np.geomspace(3.0 * tcs, 0.005 * tcs, n):   # 固定温度、收敛测量
        x, _ = solve_multi(D, Ccap, lam_cap, x0s, theta0=th, theta_min=th, gamma=1.0, seed=seed,
                           max_inner=3000, s=s, lam_commit=lam_commit)
        mp = float(x[:, 1:, :].max(2).mean())
        if prev is not None and (prev[1] - thresh) * (mp - thresh) < 0:
            (t0, y0), (t1, y1) = prev, (th, mp)
            return t0 + (thresh - y0) * (t1 - t0) / (y1 - y0)
        prev = (th, mp)
    return prev[0]


# ---------------- 裁判:N=2 向量化联合枚举(精确) ----------------
def brute_force_2uav(D, Ccap, lam_cap, x0s):
    """joint F = F_tbc(a) + F_tbc(b) + F_cap(occ_a+occ_b)。只在 λ>0 的格子上算 F_cap(其余恒 0)。
    返回 (F_opt, mask(P,P) 最优布尔阵, idx() 轨迹→行号, 例子, n_opt)。P = M^(K-1)。"""
    N, M = x0s.shape
    K = Ccap.shape[0]
    assert N == 2, "裁判是 N=2 专用(更大 N 用 LAP 当标尺)"
    starts = x0s.argmax(1)
    tails = np.array(list(itertools.product(range(M), repeat=K - 1)))   # (P, K-1),末位变最快
    P = len(tails)

    def leg(start):
        full = np.concatenate([np.full((P, 1), start, dtype=int), tails], axis=1)   # (P,K)
        cost = np.zeros(P)
        for k in range(K - 1):
            cost += D[full[:, k], full[:, k + 1]]
        return full, cost

    fullA, tbcA = leg(starts[0])
    fullB, tbcB = leg(starts[1])
    cells = np.argwhere(lam_cap > 0)                     # 活跃格 (k,µ)
    lamc = lam_cap[cells[:, 0], cells[:, 1]]
    Cc = Ccap[cells[:, 0], cells[:, 1]]
    occA = np.stack([(fullA[:, k] == mu).astype(float) for k, mu in cells], 1)   # (P, n_cells)
    occB = np.stack([(fullB[:, k] == mu).astype(float) for k, mu in cells], 1)
    Fj = tbcA[:, None] + tbcB[None, :]
    for c in range(len(cells)):
        dev = occA[:, None, c] + occB[None, :, c] - Cc[c]
        Fj = Fj + 0.5 * lamc[c] * dev ** 2
    F_opt = float(Fj.min())
    mask = np.isclose(Fj, F_opt, atol=1e-9)
    ia, ib = map(int, np.argwhere(mask)[0])

    def idx(traj0):                                      # 轨迹(0-based, 含起点)→ 行号
        v = 0
        for m in traj0[1:]:
            v = v * M + int(m)
        return v

    example = (tuple(int(v) + 1 for v in fullA[ia]), tuple(int(v) + 1 for v in fullB[ib]))
    return F_opt, mask, idx, example, int(mask.sum()), Fj   # Fj 一并返回,供自校准(对表 compute_F)


# ---------------- 审计 ----------------
def audit_multi(name, spec, n_seeds=5):
    D, Ccap, lam_cap, x0s = build_multi(**spec)
    N, M = x0s.shape
    K = Ccap.shape[0]
    F_opt, mask, idx, opt_example, n_opt, _Fj = brute_force_2uav(D, Ccap, lam_cap, x0s)
    tc = measure_theta_c_multi(D, Ccap, lam_cap, x0s)
    tcs = theta_c_scalar_multi(D, Ccap, lam_cap, N)

    rows, x_show = [], None
    for sd in range(n_seeds):
        x, dx = solve_multi(D, Ccap, lam_cap, x0s, theta0=0.95 * tc, theta_min=0.02 * tc, seed=sd)
        if sd == 0:
            x_show = x.copy()
        trajs0 = [tuple(int(v) for v in x[i].argmax(1)) for i in range(N)]        # 0-based
        xc = np.zeros((N, K, M))
        for i, tj in enumerate(trajs0):
            xc[i, np.arange(K), list(tj)] = 1.0
        Fc = compute_F(xc, D, Ccap, lam_cap)["F_total"]
        occ_crisp = xc.sum(0)                            # s=0:crisp 占用
        act = lam_cap > 0
        collide = bool((occ_crisp[act] > Ccap[act] + 1e-9).any())    # 两架挤同一单
        unserved = int(np.round((Ccap[act] - occ_crisp[act]).clip(0).sum()))      # 漏单数
        in_opt = bool(mask[idx(trajs0[0]), idx(trajs0[1])])
        sat = float(x[:, 1:, :].max(2).mean())
        rows.append(dict(trajs=tuple(tuple(v + 1 for v in tj) for tj in trajs0), F=Fc, gap=Fc - F_opt,
                         dx=dx, sat=sat, in_opt=in_opt, collide=collide, unserved=unserved))

    checks = {
        "gap=0":  all(abs(r["gap"]) < 1e-6 and r["in_opt"] for r in rows),
        "全接0撞": all((not r["collide"]) and r["unserved"] == 0 for r in rows),
        "收敛":   all(r["dx"] < 1e-3 for r in rows),
        "饱和":   all(r["sat"] >= SAT_REQ for r in rows) or (SAT_TIE_AWARE and n_opt > 1),
    }
    return dict(name=name, F_opt=F_opt, n_opt=n_opt, tc=tc, tcs=tcs, rows=rows, x=x_show,
                arrays=(Ccap, lam_cap), opt_example=opt_example, checks=checks,
                all_pass=all(checks.values()), spec=spec)


def collision_rate(spec, n_seeds=20):
    """撞车率(交叉对表 yueyan_meanfield B3 口径:精确对称对、多 seed、看 argmax 撞不撞)。"""
    D, Ccap, lam_cap, x0s = build_multi(**spec)
    N = x0s.shape[0]; K = Ccap.shape[0]; M = Ccap.shape[1]
    tc = measure_theta_c_multi(D, Ccap, lam_cap, x0s)
    hits = 0
    for sd in range(n_seeds):
        x, _ = solve_multi(D, Ccap, lam_cap, x0s, theta0=0.95 * tc, theta_min=0.02 * tc, seed=sd)
        xc = np.zeros((N, K, M))
        for i in range(N):
            xc[i, np.arange(K), x[i].argmax(1)] = 1.0
        act = lam_cap > 0
        if (xc.sum(0)[act] > Ccap[act] + 1e-9).any():
            hits += 1
    return hits, n_seeds


# ---------------- 可视化:每场景一行 = [UAV1 概率矩阵 | UAV2 概率矩阵 | 联合轨迹 vs 最优例] ----------------
def visualize_multi(results, fname="BoHan_Scheduler_Multi_viz.png"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    UAV_COL = ["#c00000", "#1f77b4"]                     # UAV1 红、UAV2 蓝
    nrow = len(results)
    fig, axes = plt.subplots(nrow, 3, figsize=(16.5, 4.9 * nrow))
    axes = np.atleast_2d(axes)

    def grid(ax, K, M, Ccap, lam_cap):
        for g in range(M + 1): ax.axvline(0.5 + g, color="0.85", lw=0.6, zorder=0)
        for g in range(K + 1): ax.axhline(0.5 + g, color="0.85", lw=0.6, zorder=0)
        for k in range(K):
            for mu in range(M):
                if lam_cap[k, mu] > 0:
                    ax.add_patch(Rectangle((mu + 0.5, k + 0.5), 1, 1, fill=False,
                                           edgecolor="#ff8c00", lw=2.2, zorder=3))
        ax.set_xticks(range(1, M + 1)); ax.set_yticks(range(1, K + 1))
        ax.set_xlim(0.5, M + 0.5); ax.set_ylim(0.5, K + 0.5)
        ax.set_xlabel("position mu"); ax.set_ylabel("time k")

    for r_i, r in enumerate(results):
        Ccap, lam_cap = r["arrays"]
        K, M = Ccap.shape
        ks = np.arange(1, K + 1)
        r0 = r["rows"][0]
        for i in range(2):                               # 每架自己的概率矩阵(co-supervisor 要的图)
            ax = axes[r_i, i]
            ax.imshow(r["x"][i], origin="lower", cmap="Greens", aspect="auto",
                      extent=[0.5, M + 0.5, 0.5, K + 0.5], vmin=0, vmax=1, alpha=0.6)
            grid(ax, K, M, Ccap, lam_cap)
            for k in range(K):                           # 有绿色的格子标上概率值(BoHan 的 Fig5 风格)
                for mu in range(M):
                    p = r["x"][i][k, mu]
                    if p >= 0.05:
                        ax.text(mu + 1, k + 1, f"{p:.2f}", ha="center", va="center",
                                color="white" if p > 0.55 else "#1a3a1a", fontsize=7, zorder=6)
            ax.plot(np.array(r0["trajs"][i]), ks, "-o", color=UAV_COL[i], lw=2, ms=5, zorder=5)
            ax.set_title(f"{r['name']}  UAV{i+1} soft x + argmax", fontsize=10)
        ax = axes[r_i, 2]                                # 联合面板
        grid(ax, K, M, Ccap, lam_cap)
        for i in range(2):
            ax.plot(np.array(r["opt_example"][i]), ks, "--", color="0.45", lw=1.6, zorder=4,
                    label="optimal example" if i == 0 else None)
            ax.plot(np.array(r0["trajs"][i]), ks, "-o", color=UAV_COL[i], lw=2, ms=5, zorder=5,
                    label=f"UAV{i+1}")
        ax.legend(fontsize=8, loc="upper right")
        ax.set_title(f"joint: gap={r0['gap']:+.1f}  collide={r0['collide']}  unserved={r0['unserved']}\n"
                     f"sat={r0['sat']:.2f}  n_opt={r['n_opt']}  theta_c={r['tc']:.2f}  "
                     f"{'PASS' if r['all_pass'] else 'FAIL'}", fontsize=10)
    fig.suptitle("Multi-UAV (N=2, s=0) audit — red/blue=UAVs, gray dashed=one optimal pair, orange=delivery",
                 fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    out = os.path.join(OUT_DIR, fname)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"saved -> {out}")


# ---------------- 主流程 ----------------
if __name__ == "__main__":
    np.set_printoptions(precision=3, suppress=True)
    SCEN = {
        "S3@N=2": dict(M=5, K=5, starts=(2, 4), deliveries=[(3, 1), (3, 5)]),   # 单架时 gap=+2 的那题
        "S4@N=2": dict(M=5, K=5, starts=(3, 3), deliveries=[(5, 1), (5, 5)]),   # 精确对称自指派(yueyan 同款)
    }
    results = []
    for name, spec in SCEN.items():
        r = audit_multi(name, spec)
        results.append(r)
        c = r["checks"]
        print(f"\n=== {r['name']} ===   F_opt={r['F_opt']:.4f}  n_opt={r['n_opt']}  "
              f"θc实测={r['tc']:.3f}(标量参考 {r['tcs']:.2f})")
        for sd, row in enumerate(r["rows"]):
            print(f"  seed{sd}: {row['trajs']}  gap={row['gap']:+.3f}  撞={row['collide']}  "
                  f"漏={row['unserved']}  |dx|={row['dx']:.1e}  sat={row['sat']:.3f}")
        print(f"  → gap=0:{'✓' if c['gap=0'] else '✗'}  全接0撞:{'✓' if c['全接0撞'] else '✗'}  "
              f"收敛:{'✓' if c['收敛'] else '✗'}  饱和:{'✓' if c['饱和'] else '✗'}"
              f"{'(tie-aware)' if SAT_TIE_AWARE and r['n_opt'] > 1 else ''}   "
              f"{'★ PASS' if r['all_pass'] else '⚠ FAIL'}")

    hits, tot = collision_rate(SCEN["S4@N=2"], n_seeds=20)
    print(f"\n交叉对表:S4@N=2 精确对称对,{tot} seeds 撞车率 = {hits}/{tot}"
          f"  (yueyan_meanfield B3 口径:精确等距 200 seeds → 0%)")

    visualize_multi(results)
