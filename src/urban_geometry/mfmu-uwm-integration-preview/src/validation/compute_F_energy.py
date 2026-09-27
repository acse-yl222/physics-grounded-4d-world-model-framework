"""
compute_F_energy.py  ——  从概率矩阵 x 算【能量 F】(总代价),完全忠于 paper 0630。
(命名:macOS 大小写不敏感,compute_F.py 会和 compute_f.py 撞成同一文件,故加 _energy / _meanfield 区分。)

    F_tbc = Σ_i Σ_{k=1}^{K-1} x[i,k]ᵀ D x[i,k+1]                     (eq15-17;eq17 的 ½ 是矩阵写法)
    F_cap = ½ Σ_{k,ν} λcap[k,ν]·( Σ_i y[i,k,ν] − Ccap[k,ν] )²        (eq29),y=(1−s)x(eq25)
    F     = F_tbc + F_cap

输入:概率矩阵 x —— 形状 (K,M) 单架,或 (N,K,M) 多架。
输出:F_tbc、F_cap、F_total(都是标量)。
F 是一个【标量总账】,用来评估"这整条(些)轨迹总代价多少";它不是用来算概率的(那是 f 的活,见 compute_f.py)。
"""
import numpy as np


def compute_F(x, D, Ccap, lam_cap, s=None):
    """x:(K,M) 或 (N,K,M) 概率矩阵。D:(M,M) 距离。Ccap/lam_cap:(K,M)。s:(K,M) 或 (N,K,M) 或 None(=0)。"""
    x = np.asarray(x, float)
    if x.ndim == 2:                                    # (K,M) → 当作 1 架 (1,K,M)
        x = x[None]
    N, K, M = x.shape
    s = np.zeros((N, K, M)) if s is None else np.broadcast_to(np.asarray(s, float), (N, K, M))

    # ---- F_tbc:对每架、每条相邻时间边 (k → k+1) 求 x_kᵀ D x_{k+1}(eq15-17)----
    F_tbc = 0.0
    for i in range(N):
        for k in range(K - 1):                         # 边 k→k+1,共 K-1 条
            F_tbc += float(x[i, k] @ D @ x[i, k + 1])

    # ---- F_cap:½ Σ λcap (Σ_i y − Ccap)²,y=(1−s)x(eq29 + eq25)----
    y = (1.0 - s) * x                                  # (N,K,M) 有效占用
    occ = y.sum(axis=0)                                # (K,M) = Σ_i y(每个 (k,站) 的总占用)
    F_cap = 0.5 * float(np.sum(lam_cap * (occ - Ccap) ** 2))

    return dict(F_tbc=F_tbc, F_cap=F_cap, F_total=F_tbc + F_cap)


# ============================ 演示 scenario(和 BoHan Scheduler.py 同款,可改)============================
def build_scenario(M=5, K=5, start=3, deliveries=((4, 1), (5, 5)), harbors=()):
    """返回 D, Ccap, lam_cap, s, x0。改这里的 start/deliveries/harbors 去匹配你的实验。
    (默认场景与 BoHan Scheduler.py / validate_scheduler.py 一致:start=3,deliveries=(4,1),(5,5)。)"""
    pos = np.arange(1, M + 1, dtype=float)
    D = np.abs(pos[:, None] - pos[None, :])            # D[ν,µ]=|posν-posµ|(eq15)
    colsum = D.sum(0)
    i0 = lambda v: v - 1
    Ccap = np.zeros((K, M)); lam_cap = np.zeros((K, M)); s = np.zeros((K, M))
    x0 = np.zeros(M); x0[i0(start)] = 1.0
    for k, mu in deliveries:                            # 投递:Ccap=1,λcap=2·colsum(eq90;全局平均版=eq92)
        Ccap[i0(k), i0(mu)] = 1.0; lam_cap[i0(k), i0(mu)] = 2.0 * colsum[i0(mu)]
    for k, mu in harbors:                               # 安全港:s=1 + 该时刻全站 λcap 激活
        s[i0(k), i0(mu)] = 1.0
        for nu in range(M):
            lam_cap[i0(k), nu] = 2.0 * colsum[nu]
    return D, Ccap, lam_cap, s, x0


if __name__ == "__main__":
    np.set_printoptions(precision=3, suppress=True)
    D, Ccap, lam_cap, s, x0 = build_scenario(harbors=((2, 2), (3, 2)))
    # 演示用主实验的最优 crisp 轨迹(= validate Test1 暴力枚举的全局最优):k=1..5 在站 3,2,2,1,5 → F=6.0
    traj = [3, 2, 2, 1, 5]
    x = np.zeros((5, 5))
    for k, mu in enumerate(traj):
        x[k, mu - 1] = 1.0
    out = compute_F(x, D, Ccap, lam_cap, s)
    print("演示:crisp 轨迹", traj)
    print(f"  F_tbc = {out['F_tbc']:.3f}")
    print(f"  F_cap = {out['F_cap']:.3f}")
    print(f"  F_total = {out['F_total']:.3f}")
    print("\n用法:  from compute_F_energy import compute_F, build_scenario")
    print("       D,Ccap,lam_cap,s,x0 = build_scenario(...)")
    print("       out = compute_F(你的x, D, Ccap, lam_cap, s)   # x 可以是 (K,M) 或 (N,K,M)")
