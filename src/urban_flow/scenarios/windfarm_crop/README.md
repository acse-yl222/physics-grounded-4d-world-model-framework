# 全部 23 台风机的裁剪对照试验

独立输出，不改变原 region 数据或求解器。

- 由原 GLB 的轮毂和叶片顶点确定全部风机位置与近似叶轮半径；不是厂商实测参数。
- 5D 上游、8D 下游、3D 横向最低余量，向多重网格兼容尺寸补齐。
- 区域 4096×2048×512 m；原点 (-1776,-992,0)；4 m 等距网格 (128,512,1024)，67,108,864 cells。
- 地形从原 GLB 重新光栅化，保留塔筒、机舱和其他静态几何；移除 69 片叶片和 23 个 hub/spinner。
- 地形原始 DSM 约 30 m；4 m 计算网格不增加实测地形信息。原数据覆盖 93.75%，外围采用最近边缘延拓。
- 假设 +x 来流和叶轮迎风，U0=8 m/s，离地速度剖面 8*(1-exp(-h/12))，无气象标定。
- C′T=4/3（控制组为零），rho=1.225，轴向平滑 sigma=8 m、径向边缘宽度 4 m，5 秒力启动斜坡。
- 力采用 https://lesgo.me.jhu.edu/actuator-disk.html 的归一化轴向阻力形式，以瞬时盘区加权速度估计，不含时间滤波、旋转扭矩或功率。
- 使用 AI4Urban 参考算子，本独立试验将空间梯度乘二，修正线性场半增益；10 次 MG，出口速度零梯度、压力零，入口固定剖面。
- 控制组和致动盘组初值一致，每组 400 步，dt=0.025 s，共 10 秒，每 20 步存一帧，21 帧。
- 初试 dt=0.1 s 在第 60 步超过 CFL 阈值，停止并保留在 `control_dt01_stopped`，不作为最终对照。

运行位置：workstation UrbanWorldModel 项目，`.venv-region/bin/python`。

```sh
python input/windfarm_crop/prepare.py --plan-only
python input/windfarm_crop/prepare.py
python input/windfarm_crop/run.py --case control --steps 400
python input/windfarm_crop/run.py --case actuator --steps 400
python input/windfarm_crop/verify.py
```

输出在 `output/region_crop/geometry`、`visualizer/scenes/windfarm_crop`。
展示原生 4 m 地形随动切片、相同色标的控制/致动盘场、控制减去致动盘的速度差、全部风机及单机局部视图。
这是启动过程，未形成全场充分发展的尾流，不作稳态、工程精度或发电量结论。
压力投影残差、边界位置、网格/时间收敛及湍流模型仍需验证。
