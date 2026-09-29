# 转子模型复现 → windfarm → 网站动画

用户目标：完整复现讨论中的转子受力模型和固定风洞验证，迁移至现有 23 台风机
场景，更新网站动画。采用 10 m/s；4 m/s 已由用户撤销。均匀网格是当前首选。
本记录不是完成声明。原始风场和已经发表的资源版本保留。

## 完成证据清单

- [ ] 核实正式论文与预印本差异、风洞尺寸及轮毂位置、Gaussian 定义、面积约定、
  湍流入口、壁面处理和参考剖面；未公开参数标明假设，不伪称原始输入。
- [ ] 完整加权致动盘：空间权重、相对入流、受力与反作用、任意方向、平台力矩、
  指定推力模式；与独立参考计算比对，检查均匀网格偏移／旋转敏感性。
- [ ] 10 m/s 固定风洞：无滑移底部、侧面／顶部滑移、出口、k-epsilon 和 k-omega SST；
  1D/3D/5D 剖面、至少三个网格及稳态残差／载荷检查。实验数据比较需真实来源。
- [ ] 将验证过的受力模型与流动处理迁移到真实 windfarm 场景，保留坐标、地形、
  23 台风机身份、输入哈希、显式新参数和保存时刻。验证力守恒、质量守恒及稳定性。
- [ ] 协议运行和动画数据导出；渲染器读取实际时间轴与元数据，不硬编码旧 300 s／2 s。
  展示动画转速与真实求解量清楚区分，不将单相致动盘称为叶片解析。
- [ ] 桌面／移动浏览器回放、暂停、时间选取、图例、资源错误恢复与性能检查。
- [ ] 发布版本化新结果和网站代码，检查在线实际加载的新版本及旧链接兼容。

## 已有证据（2026-09-29）

- `paper_rotor_10ms_results.md` 记录现有 4 cm／2 cm MAC 数值试验：其底部滑移、
  无湍流闭合，只是早期受力验证，不能替代上面的风洞验证。
- Docker 服务可用，官方 `opencfd/openfoam-default:2312` 已拉取；镜像 digest：
  `sha256:097e45046a74ee1dae3e6135df0c42723ba55092d246e7c9932f3bfa1e89b7b2`。
  参考求解环境与主机 Python/GPU 环境隔离，尚未运行完整风洞。
- 正式版 Elsevier 接口仅返回元数据；作者预印本正文可读。引用版本必须明确。
- 网站当前仍加载 `published_movie_v1`（旧 2 m MAC 8 m/s 实验），动画时间索引
  硬编码 2 s，数据选择默认旧 200–300 s 平均。尚未更新或发布。

## 接下来的工作

官方 OpenFOAM 独立源项的符号、单位、并行归约和两种闭合的数值收敛已检查。
接下来核实原始风洞输入与实验剖面，并进行网格敏感性验证。完成前不将新风场或网站标记为完整复现。

## 本轮进展与可恢复运行

- `openfoam_reference.py` 已生成和实际运行官方 OpenFOAM 2312 的独立 C++ 加权
  致动盘源项。4 cm 均匀网格，底部 noSlip/壁面函数，侧面和顶部对称滑移。
  不再依赖此前没有黏性／湍流的 MAC 来冒充 RANS 验证。
- 单进程 50 次迭代运行 `20260929T014936Z_f162249d` 成功；四进程运行
  `20260929T015049Z_70be8daf` 成功。初始均匀盘区速度 10 m/s 时源项推力
  26.365812 N，随诱导作用减速；不能与上游 10 m/s 的理想稳态推力混淆。
  源项积分守恒误差约 1e-14 N。50 次迭代尚未收敛，分析器正确拒绝收敛声明。
- 两个四进程长运行已成功退出，分析器确认数值收敛，并保留至 `project/actuator_lab/runs/`：
  - SST：`20260929T015215Z_99dcd002`，445 次迭代，盘区速度 6.265971 m/s，推力 10.351850 N。
  - k-epsilon：`20260929T015216Z_eb992e34`，422 次迭代，盘区速度 6.295665 m/s，推力 10.450194 N。
  - 所有规定初始残差 < 1e-6，最后 100 次推力变化比例 < 6e-7，源项积分误差 < 1.4e-14 N。
  - 两个协议清单通过验证；静态剖面无物理时间轴。上述收敛不代表实验准确性已验证。
  - 域、轮毂位置、入口湍流和 Gaussian 参数仍有明确假设，不能作为完整论文复现结论。
- 新分析器输出静态 1D/3D/5D 剖面、完整日志、配置和重建输入；严格区分迭代和物理秒。
- 本地网站已改用真实保存时间插值，支持不等间隔和非零起点；仍读取旧公开数据。
  3 项时间轴测试及实际浏览器暂停／后台休眠／切换／导出性能检查通过。
- 48 项 Python 检查通过。尚未运行三网格收敛研究，尚未迁移新解至 windfarm 或发布网站。

## 新发现的文献差异

作者预印本 §3.2 写外径 0.4647 m；其引用实验的作者报告写直径约 0.9 m、
轮毂高 0.8 m、湍流强度 0.3%，测试段约 11.2×1.8×2.7 m。
这不是可静默合并的同一套输入。当前仍按预印本文字运行受力参考；完整几何和
实验剖面对齐前必须核实正式版图表或作者输入。

第一手来源：
- [论文作者预印本](https://www.researchgate.net/publication/395079413_Turbines_and_Thrusters_A_Versatile_OpenFOAM_Framework_for_Modeling_Aerial_Rotors_on_Floating_Bodies)
- [Eriksen / Krogstad 原实验报告，第 3–4 页](https://www.sintef.no/globalassets/project/deepwind-2013/deepwind-presentations-2013/f/eriksen-p.e._ntnu.pdf)
- 正式版 DOI `10.1016/j.joes.2026.07.020` 的 Elsevier API 当前只返回元数据，
  FULL 请求返回 401；网页返回 403。未将元数据当全文使用。

## 三网格敏感性验证（已启动）

- SST 8 cm：`20260929T015853Z_4ae1044e`，254 次迭代通过数值收敛审计，
  推力 6.881167 N，已保留至项目 runs。与 4 cm 的 10.351850 N 有明显差异；
  网格尺寸等于受力区厚度，不能因残差收敛而认定空间分辨率足够。
- SST 2 cm：`20260929T015854Z_ca566296`，四进程 Docker 容器
  `rotor-reference-20260929T015854Z_ca566296`；启动 session 62910。
  启动后已确认容器活跃，正在网格分解／求解。继续工作前检查真实容器及日志，勿重复启动。
- `compare_reference_grids.py` 检查至少三种网格、物理配置一致及每次运行数值收敛，
  比较推力与 1D/3D/5D 速度亏损，不把网格敏感性报告包装为实验验证或 GCI。

### 本地显示适配与检查

- 新 `layout.mjs` 从 metadata 读取显示间距、采样中心偏移和切片高度，保留世界坐标
  到 viewer 的轴变换。旧导出缺失切片高度时沿用其已知 80 m；新结果应显式声明。
- 11 项 viewer / 时间轴 / 采样位置测试通过；48 项 Python 回归通过。
- 浏览器检查首次在暂停交互断言失败（时间仍变化），同一版本重跑通过全部
  暂停、后台停止、切换、缩放和 JPEG 导出检查。记录此偶发失败，不视为已消除。
- OpenFOAM 生成器现在拒绝 thickness 与 2*sigma*cutoff 不一致的输入，避免独立
  参考与 WeightedRotor 使用不同受力支撑区；当前已运行配置均满足这一约束。
- 2 cm SST 已进入真实 SIMPLE 求解；最后检查容器使用约四个 CPU、5.7 GiB 内存，
  仍在运行，尚未收敛。网站资源尚未发布，风场尚未迁移。

## 风场迁移准备

- `project/windfarm/configs/paper_rotor_10ms.json` 显式指定用户要求的 10 m/s。
  保留场景 Ct=0.75、sigma=8 m、cutoff=2 等已有假设；未把缩比风洞 Ct=0.95／
  D=0.4647 m 强行用到约 82 m 的实际几何。入口湍流参数仍是声明的场景假设。
- `prepare_windfarm.py` 生成可追溯的均匀体素输入。最新有效准备目录：
  `cache/windfarm/paper_rotor_geometry/20260929T020224Z_14772853`。
  包含源文件哈希、源码快照、几何/配置、地形有效掩码及逐转子支撑区审计。
  之前 `20260929T020216Z_c9322d84` 含过时的几何统计字段，不用于后续迁移。
- 实际独立数组检查通过：23 台风机信息逐项等于源输入、原点和空间范围相同，
  固体网格是源子网格的保守并集，所有转子都有未截断的有效流体受力区。
  8 m 网格含 5,322,011 个流体单元；最大被固体占用的权重比例 2.713%。
  后续源项必须按流体权重体积归一化，否则掩码会损失载荷。
- 这是求解输入准备，不是风场仿真结果。尚未启动风场 RANS／瞬态求解。
- 2 cm SST 单转子容器最后检查仍活跃，已到第 67 次迭代；不应重复启动。

## OpenFOAM 风场网格接入

- `windfarm_reference.py` 已生成 23 个独立受力源项，沿用独立参考公式，各源按实际
  流体网格加权体积归一化。求解坐标为世界坐标减源 origin，转换显式记录。
- 小型真实 OpenFOAM 验证目录 `cache/actuator_lab/foam_mesh_mapping_test/20260929T020346Z_9639d412`：
  24 个原单元中选择标签 12/13/16/17 后，输出中心恰为
  (0.5,0.5,1.5)/(1.5,0.5,1.5)/(0.5,1.5,1.5)/(1.5,1.5,1.5)。
  确认 x-fastest 标签到 [z,y,x] 数组映射；新增表面归入 bottom 壁面，Mesh OK。
- 首次真实风场网格 `cache/windfarm/openfoam_reference/20260929T020358Z_a9756ed2`
  构建成功且只有一个连通区域，但完整质量检查失败：98 个 determinant=0 的流体单元。
  不用于求解。失败容器已终止，工具 session 48907 exit 1。
- 分析确认 98 个单元恰好缺少至少一个轴向的内部流体邻居。新增明确的几何规则：
  填充这些无法分辨的细缝并迭代至固定点，保存 regularized_fluid_cells.npy。
  实际只填充 98 个单元，占原流体单元 0.0018414%；原几何不修改。
  两项回归测试验证保留正常域、不修改源数组、记录准确修整掩码及固定点性质。
- 最新输入 `cache/windfarm/paper_rotor_geometry/20260929T020605Z_d9f80a4f`；
  新网格 `cache/windfarm/openfoam_reference/20260929T020613Z_da2cf399`。
  容器 `farm-mesh-20260929T020613Z_da2cf399`，工具 session 79972，正在网格重建／检查。
  后续必须检查该容器及 log.checkMesh，不重复启动；此时还没有流动求解或动画帧。
- 先前 48 项 Python 回归通过；新增两项几何规则测试另行通过。

## 真实物理时间求解已启动

- 修整后的 `20260929T020613Z_da2cf399` 通过 OpenFOAM 全拓扑／几何检查，
  `log.checkMesh` 明确 `Mesh OK.`；网格容器成功退出（session 79972 exit 0）。
- `scene_transient.py` 将 23 个源项合并为一个编译单元，各转子仍独立归约和归一化；
  使用官方 pimpleFoam + kOmegaSST，Euler 时间离散，两个 PIMPLE 外循环、两个压力校正，
  自适应 dt<=0.2 s、maxCo=0.5，5 s 载荷启动渐增。先运行 2 s 冒烟测试。
- 每 2 s 输出真实物理时间的地形随形 80 m AGL 切片；保留最新两个全场检查点。
  OpenFOAM 内部 local XYZ 到世界坐标的 origin 平移仍显式保存，不虚构 t=0 数据帧。
- 初次配置遇到源码快照不可覆盖检查；未启动求解。已改为独立
  transient_source_snapshot.tar.gz / transient_provenance.json 保留网格阶段原快照，
  补齐这些文件后才启动当前求解。当前配置和快照对应实际执行设置。
- 活跃容器 `farm-flow-20260929T020613Z_da2cf399`；启动工具 session 30702。
  日志 `log.pimpleFoam` 已出现物理时间 0.117647058824 s 的全部 23 台载荷，
  源项守恒误差约 1e-11 N；尚未完成 2 s，也未审计尾流、质量守恒或采样输出。
- `scene_diagnostics.py` 区分同一时间的 PIMPLE 重复计算，保留每台最后一次载荷，
  拒绝缺失风机、不完整运行、倒退时间和非有限值。两项新增针对性测试通过。
- 本轮全量 Python 回归 52 项通过。单转子 2 cm SST 仍在继续运行，未重启。

## 动画数据导出与适配

- `export_scene_movie.py` 从实际 cloud 采样坐标映射回规则切片，校验 XY 中心和离地高度，
  拒绝重复/错位点；缺失采样和原始地形覆盖以 NaN/掩码保留。仅接受成功到达目标时间
  的瞬态运行，逐帧必须有同一物理时刻的完整转子诊断，不制造初始帧。
- 导出可声明任意数量 u-bin 分块；metadata 显式包括真实时间、8 m 显示间距、中心偏移、
  求解器和验证状态。导出标记 publish_ready=false；短冒烟运行不自动成为发布结果。
- 现有网站读取这些元数据，并支持 comparison_keys=[] 的纯时序数据，不再强制加载
  四组旧比较场、四个固定分块或展示旧 MAC 2 m 描述。保留旧数据兼容分支。
- 浏览器原性能回归通过；新增 `browser_wind_metadata.cjs` 用旧真实数据作为明确标记
  的接口测试夹具，验证纯时序模式没有旧比较请求/标签、metadata 说明显示正确。
  这个测试不代表新风场已求解或发布。
- 54 项 Python、11 项 JS 测试通过。导出程序尚未用于真实完成运行，因为 2 s 冒烟
  当前仍在进行。活跃容器和工具句柄与上一节相同，最后检查二者均使用约四个 CPU。

## 续算与导出门槛

- 瞬态审计新增真实 Courant 数和质量连续性检查；数值冒烟通过要求 maxCo<=0.55、
  最终局部连续性误差 <1e-5、源项积分相对误差 <1e-8。未将这些条件称为实验精度验证。
  不满足条件的运行不能进入动画导出或自动续算。
- `resume_scene.py` 已实现续算准备：仅接受干净结束、通过上述检查的运行；所有分区
  必须具有目标时刻的 U/p/k/omega/nut/phi 完整检查点。保存前段配置、控制字典、日志
  和诊断后从 latestTime 接续，不重新分解或清空旧日志。全场检查点改为 20 s 间隔，
  切片仍按 2 s 输出。尚未执行续算，因为首次 2 s 运行未完成。
- 新回归验证“成功结束”但 Courant 数过大的运行仍无法通过数值门槛；相关三项通过。
  此前全量 54 项回归通过，随后添加了该一项检查。
- 真实试运行最后观察已超过 1.27 s，局部连续性误差降至约 4e-8；容器及 session 30702
  仍活跃。单转子 fine reference 也仍在运行，不能宣布收敛或重复启动。

## 2 s 真实试运行完成，300 s 续算已启动

- 2 s 运行成功退出（session 30702 exit 0）。数值审计：maxCo=0.505858562819，
  最终局部连续性误差 3.42776288753e-12，累积 4.30953241271e-8，
  最大源项积分误差 2.28174030780675e-9 N；23 台完整，冒烟门槛通过。
- 真正的 2 s cloud 输出为 `postProcessing/terrainSlice/2/slice_U.xy`。
  求解器提示 131072 个采样位置中 41 个不在流体域；导出保持为空，另屏蔽原始地形
  覆盖外区域。最终 122839 个有限像素；显示轴向速度范围约 0.366–17.609 m/s。
- `package_scene.py` 连同重建输入、源码、配置、日志、掩码和显示文件输出协议结果。
  首两次 schema 校验捕获 simulation 大小写和 artifact 缺 media_type，均未保留；
  修正后有效包 `cache/windfarm/openfoam_scene_export/20260929T021521Z_4624c9da`
  通过完整协议验证，并保留至 `project/windfarm/runs/20260929T021521Z_4624c9da`。
  仅含真实 t=2 s 一帧，不代表最终动画或实验验证，publish_ready=false。
- `browser_wind_run.cjs` 实际加载上述新数据和原风机几何；23 台、10 m/s、新求解器
  标签、无旧比较场均通过。截图已目视检查，位于
  `cache/framework/browser/windfarm-uran/20260929T021521Z_4624c9da.png`。
- 完整检查点经核验后，已从 t=2 s 续算到目标 300 s。旧配置/日志/2 s movie 保存至
  源算例 `completed_through_2s/`，续算追加日志，未重启初始状态。
  当前活跃容器仍名 `farm-flow-20260929T020613Z_da2cf399`，但新的工具 session 为 20185；
  原 session 30702 已完成。后续检查新句柄及容器，不重复启动。
- 单转子 2 cm SST 仍在运行，最后观察第 292 次迭代，尚未达到残差门槛。

## 独立受力对照与发布入口

- `compare_reference_force.py` 读取真正的 OpenFOAM 4 cm 最终 U 场，以原 PyTorch
  WeightedRotor 重新积分，未使用合成均匀流代替参考场。结果保存
  `project/actuator_lab/independent_force_comparison.json`，记录两个场的 SHA-256。
  SST 推力差 7.92e-9 N，k-epsilon 推力差 7.09e-9 N；Torch 自身积分误差 <6e-15 N。
  说明相同收敛场上的两个受力实现一致，不构成实验准确性声明。
- 网站构建器的风场 URL 已改为从 public-scenes 的资源 ID 派生，避免首页目录和
  动画实际加载版本不一致；歧义或越界版本被拒绝。两项针对性测试通过。
  当前目录仍指定旧公开资源，不曾提前切换或发布未完成结果。
- 已发现既有 `cache/framework/english-publication` 干净 detached worktree，但未修改；
  app 的 list_artifacts 查询长时间未返回，未据此创建额外工作树。
- 风场 300 s 续算（session 20185）与单转子细网格（session 62910）均仍活跃，
  本轮最后观察风场约 3.09 s。继续检查真实句柄，不因较长计算时间重启。

## 任意轴向边界修复与新增实际采样

- 续算采样已出现 t=4.053335639 s，而非恰好 4 s。逐点坐标/高度检查通过，
  与 t=2 s 的缺失掩码完全相同，有限点仍为 122839；两帧最大速度变化约 5.083 m/s。
  审计 `intermediate_sampling_audit.json` 在源算例内，明确 run_complete=false。
- 在 WeightedRotor 中复现到任意轴向缺陷：axis=[1,1,1]，轴线上 xyz=[1,1,1]，
  双精度径向平方因消减误差变为 -1.33e-15，导致有效中心线点被排除。
  已像独立 C++ 实现一样 clamp_min(0)，并拒绝零或非有限轴向。两项回归覆盖。
- 全量 59 项测试通过；修复后重新对比两份 OpenFOAM 最终场，推力和守恒结果
  与之前一致，报告 `cache/actuator_lab/force_after_axis_fix.json`。
  当前实际运行的 C++ 源项原先已有径向平方截断，不需要因该 Torch 修复重启。
- 两个容器仍活跃，风场最后观察约 5.36 s。尚未满足完整复现/最终动画发布条件。

## 网格位置和任意方向的独立采样审计

- `audit_grid_alignment.py` 对 3 个网格、3 个轴向、3 个亚单元平移共 27 组检查。
  使用解析加权均值为 10 m/s 的仿射速度场，以隔离几何积分误差，不混入流动解误差。
- `rotor_grid_alignment_audit.json` 记录每组实际采样速度和积分守恒；最大速度偏差：
  8 cm 为 0.0800 m/s，4 cm 为 0.009277 m/s，2 cm 为 0.004604 m/s。
  27 组均有有效支撑，载荷积分误差 <1e-10 N。该结果不证明 8 cm 流动解足够准确，
  更不替代真实实验或正在进行的细网格流场收敛。

## 并行性能对照（独立分支，未替换主运行）

- 当前四进程风场预计仍需数小时。主机有 16 物理核/32 线程，准备从已保存的 2 s
  检查点做 16 进程有界对照，不改动活跃原运行或覆盖其输出。
- `benchmark_parallel_scene.py` 复制必要网格与 4 个原分区的 t=2 场，逐场记录 SHA-256，
  使用官方 redistributePar 重新分配为 16 分区，再从 2 s 算到 6 s。
  分区检查成功，约 532 万流体单元均衡分配；内存约 8 GiB，限制 28 GiB/16 CPU。
- 分支目录 `cache/windfarm/parallel_scene_benchmark/20260929T022816Z_b3f45d4b`；
  容器 `farm-benchmark-20260929T022816Z_b3f45d4b`，启动 session 28634。
  最新观察到 3.230769231 s，仍活跃；源主运行约 7.488148174 s，仍活跃。
- 对照使用 2 s 全场写盘间隔，以保证结束时有可恢复检查点；主续算为 20 s。
  因 adjustableRunTime 会影响步长，对照不是逐位相同的并行确定性试验；比较需使用
  真实物理时间，并报告时间步和同时运行的负载影响。未宣称已有加速收益。
- scene_transient.execute 已按配置进程数执行，支持后续选择经过验证的分区；
  两项测试验证续算不重新分区/覆盖旧日志、活跃任务不能重复启动。
- 对照尚未完成或选择为主分支；若未来选用，需保留父 2 s 检查点重建材料，
  更新 benchmark_only 状态和完整来源记录，再考虑替代原主运行。

## 已选择 16 进程分支作为主运行（重要句柄变更）

- 16 进程 2→6 s 对照成功结束（session 28634 exit 0）。maxCo=0.511746，
  最终局部连续性误差 3.3364e-12，源项积分误差 4.5635e-9 N，23 台完整。
- `compare_parallel_scene.py` 以已有参考时刻内部插值进行比较，不外推；核验物理配置、
  源项和求解离散字典一致。结果 `project/windfarm/parallel_comparison_4_16.json`：
  最大相对载荷差 0.49737%；4 s/6 s 切片相对 L2 差 0.011657% / 0.004225%。
  在共同 2.5–5.5 s 区间，参考耗时 463.38 s、候选 328.50 s，观测速度比 1.410589。
  有自适应步长/写盘与共享主机影响，不冒充严格 strong scaling 或实验验证。
- 已核对原始父检查点逐场哈希，并保存约 560 MiB 的 `parent_checkpoint_2s.tar.gz`，
  含父分区网格和 t=2 场；候选源码快照、对照记录也已保留。打包器将一并收录这些
  本地重建材料；不会因为存在该文件而自动公开上传全部检查点。
- 候选 `20260929T022816Z_b3f45d4b` 已标记 benchmark_only=false，从完整 6 s 检查点
  续算到 300 s。6 s 阶段配置/日志/诊断保存至 completed_through_6s。
  **当前主容器：`farm-flow-20260929T022816Z_b3f45d4b`；当前主 session：71704。**
- 原四进程任务在确认新主进程已进入求解后，有意停止以释放资源（不是观察超时重启）。
  旧源目录 `20260929T020613Z_da2cf399` 原始数据全部保留；status=superseded，
  intentional_stop=true，replacement_case 指向新主。旧 worker 的退出码 137 和包装器
  异常保存在 execution_exit.json；这是 Docker 有意结束冗余进程导致，不是数值崩溃。
  旧最后启动时间约 9.1128 s，其 >2 s 场不会混入新分支。旧 session 20185 已终止，勿恢复。
- 新主最新约 6.8183 s。2 cm 单转子参考仍是原容器、session 62910，尚未终止。

## 发布兼容性与运行观察

- 只读核对了资源仓库当前 resources.json 和 tools/check_resources.py。
  公开 `windfarm_geometry_published_v1` 的 GLB SHA-256 为
  b457fe574a94ca85b4b6a4c5431981982af6af6a125e214cd5ba12da713b7812，
  与场景输入 metadata 的 source_sha256 完全一致；可以复用现有公开几何。
  新结果应新增不可变 runs 版本并更新场景资源索引，不能覆盖 published_movie_v1。
  尚未克隆/修改/发布资源仓库。
- 16 进程主任务和单转子细网格均仍活跃，最新观察分别约 9.4161 s / 第 495 次迭代。
  当前主要工作是等待真实计算与后续验证；未将代码测试或预览视为完整复现完成。

## 续算检查点核验

- 主任务已完成 t=26 s 检查点并继续推进至 t>27 s；16 个分区各自的 U、p、k、omega、nut、phi 均存在且非空，检查点普通文件合计 442,317,616 字节。
- 从 t=6 s 恢复后，20 s 写入间隔对应首个新完整检查点 t=26 s，不能将日志启动 t=20 s 误认为已保存完整场。
- terrainSlice 按实际采样时间记录；已检查 t=24.06789601 s 的 131,031 个采样点，各分量均有限。此前 t=20.04267937 s 与 t=2 s 的采样位置逐点一致。
- 单转子 2 cm 参考仍在运行：第 480 至 580 次完整迭代各主要初始残差下降，但尚未满足收敛阈值。不得用中途推力或残差趋势宣称网格验证通过。
- 两个容器均经实时检查为运行中；目标仍为完成验证、场景迁移与网站更新，未发布新动画。

## 细网格完成与三档网格比较

- 2 cm SST 参考 20260929T015854Z_ca566296 在 1092 次 SIMPLE 迭代收敛，分区结果合并成功、退出码 0，已保留至 project/actuator_lab/runs/ 同名目录。所有最终初始残差低于 1e-6，局部连续性误差 1.5739452e-9，最后 100 次推力极差/均值 2.3370295e-7。推力 10.4277665366 N。
- reference_grid_comparison.json 保存 8/4/2 cm SST 对比。4→2 cm 推力增加 0.73336%；1D/3D/5D 归一化速度亏损剖面的 RMS 变化分别为 0.0553974/0.0357352/0.0227372，最大变化 0.162302/0.0814713/0.0515939。因此不能声称尾流网格无关。
- 原始并行采样存在重复坐标，重复值逐点完全相同；比较器去除相同重复点、拒绝冲突重复值，并记录原始/唯一点数。粗网格剖面线性插值至细网格实际采样坐标；原始数据未改写。
- 数值收敛通过不代表实验精度验证通过；论文参数与原始实验数据缺口仍保留。风场主计算仍在运行，尚未发布新网站动画。

## 2 cm 参考的独立载荷核验

- 将收敛的 2 cm OpenFOAM 速度场交给 Torch 受力实现重新积分，结果保存为 independent_force_comparison_2cm.json，并记录速度场 SHA-256。
- Torch 推力 10.427766522953243 N，C++ 最后记录推力 10.4277665366 N，差约 1.36e-8 N；体积力积分与转子反力之差为 1.78e-15 N，核验通过。
- C++ 记录位于最后一次速度求解之前，因此两者不是严格相同的求值时刻；此核验支持受力实现一致性，不证明实验精度。

## Completed 300 s scenario and browser verification

The 10 m/s, 23-rotor scenario completed at physical time 300 s. Its first
termination was 299.968254 s because the 20 s checkpoint interval did not
align with the endpoint. The original log and samples are archived under
`completed_through_299.968254s`; the final segment was recomputed from the
verified 286 s checkpoint with 2 s adjustable writes. No timestamps were
changed. All 96 final rank/field files were present and nonempty.

Retained run: `project/windfarm/runs/20260929T075513Z_ebd84574`.
The numerical audit passed: maximum Courant number 0.511745704763, final
local continuity error 2.11594479069e-12, maximum integrated force error
4.77739376947e-9 N. Experimental accuracy remains unvalidated.

The exported movie retains actual samples from 2 to 300 s. Browser checks
verified 10 m/s metadata, 23 rotors, playback, seeking to 150 and 300 s,
and desktop/mobile rendering without JavaScript errors. Publication is
pending; these checks do not establish agreement with paper experiments.

## Website publication verified

Resource commit: b35d6b0c6c66cfebb82ba0776b64ce36d1675b32.
Pages commit: 3538881d44994ce6f9d8809dc9f3324223e44491.
Both deployments succeeded. The public resources configuration points to
`openfoam_10ms_v1`, preserving the prior immutable version.
Live browser checks passed for 23 rotors, 10 m/s, playback, seeking to
150 and 300 s, and mobile rendering. The first attempt encountered a
transient HTTP 503 for u-4.bin; a fresh attempt passed, and the downloaded
file SHA-256 matched the retained source exactly.

Remaining completion gap: experimental fidelity. The formal paper's full
setup/author case and raw comparison data have not been obtained. Exact
Gaussian width/cutoff, inlet turbulence, geometry/domain interpretation
and the preprint rotor-diameter discrepancy remain unresolved. Numerical
convergence and implementation agreement do not resolve those omissions.
The scenario migration and website publication are complete; full paper
experimental reproduction is not established.
