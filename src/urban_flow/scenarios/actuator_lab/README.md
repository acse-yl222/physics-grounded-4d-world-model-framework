# 单致动盘高分辨率试验

独立测试叶轮轴向力，不改 windfarm 8 m 场景。假设区域 128×64×64 m，
盘中心 (32,32,32) m、直径 16 m、初始/端面来流 8 m/s、C′T=4/3、rho=1.225。
用 1 m 和 0.5 m 网格分别计算 20 秒；0.5 m 无叶轮力对照也实际推进全部时间步。
0.5 m 网格为 (z,y,x)=(128,128,256)，4,194,304 cells。

算子沿用 AI4Urban，独立试验中将 x/y/z 梯度核乘以 2，线性场增益检查为 (-1,1,1)。
原始半增益版本保留在工作站 `visualizer/scenes/actuator_lab_halfgradient`；
大风场求解器、参数和已存数据没有变化。本例底面改自由滑移，无地形、塔筒、机舱或叶片。
轴向两端固定原 u=-8，其余速度和压力沿用参考边界；这不是严格非反射风洞边界。

致动盘参考 https://lesgo.me.jhu.edu/actuator-disk.html ：
F = -rho/2 * A * C′T * Ud |Ud| * R(x)，积分 R dV=1。
本实现使用瞬时盘区加权速度、2 秒启动斜坡、轴向 sigma=2 m 的 Gaussian 和径向
1 m logistic 平滑；两种网格保持平滑宽度不变。每步对流/压力推进前后施加半步力，
验证力不增加气流动能、归一化误差和 CFL。没有盘区速度的时间滤波或粗网格修正。
无旋流、湍流模型或功率模型，不能作工程精度或真实旋转叶片模拟的结论。

工作站项目目录运行（Python 环境 `.venv-region`）：

```sh
python input/actuator_lab/run.py --cell 1
python input/actuator_lab/run.py --cell 0.5
python input/actuator_lab/run.py --cell 0.5 --ct 0
python input/actuator_lab/verify.py
```

结果：`visualizer/scenes/actuator_lab`，每种算例 41 个轮毂水平切片、末步三维速度、
完整参数和诊断指标。验证控制组恒定均匀风，比较两分辨率盘区速度及对齐后的切片。
两网格/时间步的比较不是严格的独立空间或时间收敛研究，也未与实测对照。
网页：`/viewer/actuator-lab/`。
