# 本地物理模型盘点

检查日期：2026-09-10。仅根据本地文件、checkpoint 和本次试验记录。

| 模型                   | 类型                           | 本地状态                                                                                                                                                                                                                                           |
| ---------------------- | ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DIGIT 风场             | 3D U-Net AI 代理模型           | `environment-integration/members/yiqi_temperature/models/velocity_calculation` 含代码和 `assets/digit.pth`；已在 core008 的 1 米/2 米局部几何各推理 3 帧                                                                                           |
| regression1024 风场    | VAE + 潜空间 U-Net             | `wind_temperature_teacher`、`wind_pollution_code` 含代码；缺对应风场及 VAE 权重，不能用 DIGIT 权重替代                                                                                                                                             |
| SCALED Tutorial 风场   | VAE + 潜空间 U-Net AI 代理模型 | 新增 `/home/yl222/workspace/SCALED-Tutorial/weight/inference.pth`（约 831 MiB）和 `compression.pth`（约 291 MiB）；`run_core008_scaled_wind_temperature.py` 已接入 core008 并有后台任务运行。未验证它们等同于此前 regression1024 的指定 checkpoint |
| 单步温度               | 15 通道 3D U-Net               | 原模型和 `wind_temperature_teacher/weights/temperature_one_step.pt` 均在；已验证网络张量完全相同，应计为一个模型，两份封装；严格加载通过                                                                                                           |
| Rollout 温度           | 22 通道 3D U-Net               | `environment-integration/members/yiqi_temperature/models/rollout_surrogate/outputs` 含权重；严格加载通过；本次未预测温度                                                                                                                           |
| 温度物理求解           | 数值模型                       | `environment-integration/members/yiqi_temperature/models/physical_model` 含代码；另有 `wind_temperature_teacher/code/cloud_workflow.py` 的简化参考热求解器。需要风场、初始温度及热边界/热源参数                                                    |
| 污染物浓度             | DigitUNet3D AI 代理模型        | `wind_pollution_code/code/vendor/yuhang` 含代码；缺浓度模型和配套编码器权重                                                                                                                                                                        |
| 污染物输运             | 数值模型                       | `wind_pollution_code/code/vendor/yuhang/data_generation/physical_transport.py` 等含输运和数据生成代码                                                                                                                                              |
| 健康响应、环境 routing | 占位目录                       | `environment-integration/members/ruhang_health_response` 与 `guanhao_routing` 目前只有 README 占位                                                                                                                                                 |

`pipelines/geometry/mfmu-uwm-integration-preview` 是独立的无人机调度模块，不是风场/温度求解器。

本次结果和准确性边界见 `output/core008/physics/digit_smoke/README.md`。温度模型需要历史温度和热条件，当前仅做权重加载检查，不能将其列为已完成新区域联合推理。

新增 SCALED 任务的结果路径为项目根目录 `output/core008/physics/scaled/`。检查时日志最新完成 10/40 风场步，温度阶段尚无输出；实时状态以该目录 `run.log` 为准。当前 SCALED 任务覆盖 `[64,2944,3136]`（Z,Y,X）、1 米网格，覆盖原区域水平建筑范围及部分 padding，并非完整 4096×4096×128 米域；64 米以上建筑被截断。该新几何迁移任务尚无 CFD/观测真值验证。

## 2026-09-12 新增：洪水

| 模型                   | 类型                                                                        | 本地状态                                                                                                                                                                                            |
| ---------------------- | --------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 浅水方程洪水           | 数值模型（PyTorch 模板运算，论文 S030917082500017X 的 NN4PDEs 思路）        | `pipelines/physics/flood_swe.py` + `run_core008_flood_swe.py`，已在 core008 域 1 米/4 米跑通降雨内涝场景；作者原始代码在 `~/workspace/Shallow_Water_Equations_NN4PDEs`（Carlisle 算例，未直接使用） |
| 太阳光照               | 数值模型（PyTorch 张量层：射线滑动最大值倍增网络、地平线层组、ASHRAE 清空） | `pipelines/physics/solar_np.py` + `run_core008_solar.py`，已在 core008 域 1 米算夏至/冬至阴影、SVF、辐照度（`output/core008/physics/scaled_latent/solar/`）                                         |
| Yi Qi 3-D 温度物理模型 | 数值模型（地表能量平衡 + 3-D 平流扩散）                                     | 2026-09-12 首次在 core008 域跑通（`run_core008_temperature3d_solar.py` 用 SCALED 风场建缓存），并与太阳模型耦合（`temperature3d_solar/`），整日链式 `run_core008_temperature3d_diurnal.py`          |
