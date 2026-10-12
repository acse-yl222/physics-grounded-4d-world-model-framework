# 框架结构与运行流程

本文描述当前代码结构和运行入口。目录约定、数据保留规则和结果清单格式以
[仿真与可视化协议](framework/protocol-v1.md) 为准；迁移进度和已执行的验证见
[实施记录](framework/implementation-status.md)。

## 职责划分

| 位置                                   | 内容                                                       |
| -------------------------------------- | ---------------------------------------------------------- |
| `src/`                                 | 可复用代码，按领域分包                                     |
| `project/<scene>/`                     | 场景身份、配置、输入、共享几何、保留的运行结果和视图       |
| `cache/<scene>/<simulation>/<run_id>/` | 试跑工作目录，可删除、可重算；正式结果必须先保留到 `runs/` |
| `schemas/`、`examples/`                | 协议 schema 和小型合成示例                                 |

| 包               | 职责                                                                                                                                                                  | 入口                                                                                          |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `common`         | 存储路径解析（`storage`）、协议校验（`contract`）、保留（`runs`）、bundle 导出（`export`）、源码快照（`provenance`）、本地服务（`server`）、场景流水线（`pipeline/`） | `p4d`（兼容 `uwm`）                                                                           |
| `urban_geometry` | GLB 体素化（`voxelization/`）、South Kensington Blender 建模（`agent/`）、鸟群（`birds/`）、UAV 模型（`uav/`）；`core008/` 是现有城市资产的历史脚本                   | `voxelization/prepare_glb.py`；Blender 脚本；`python -m urban_geometry.birds.scripts.run_sim` |
| `urban_flow`     | 求解器（`solvers/`）、风/太阳/洪水物理核（`physics/`）、风电场与致动盘实验（`scenarios/`）、转子（`paper_rotor/`）                                                    | `p4d experiment`                                                                              |
| `traffic`        | 交通训练、预测和回放导入                                                                                                                                              | `python -m traffic.train`                                                                     |
| `uav_routing`    | 地面站、Wave PDE 路径计算、审计和导出                                                                                                                                 | `python -m uav_routing.compute`，见其 README                                                  |
| `visualization`  | 统一查看器（`viewer/`、`widgets/`、`shared/`）、数据适配器（`adapters/`）、旧专用查看器（`legacy/`）                                                                  | `p4d serve`                                                                                   |

求解器不依赖浏览器，widget 不承担求解；导出适配器负责把内部结果转换为协议资产。

以下目录是上游交付或成员研究代码，保留原实验语义，框架重构不改写其算法：
`urban_geometry/mfmu-uwm-integration-preview/`、`urban_flow/physics/environment-integration/`、
`urban_flow/physics/wind_pollution_code/`、`urban_flow/physics/wind_temperature_teacher/`、
`urban_flow/reference_public/`。

## 运行流程

### 场景流水线：`p4d run <scene>`

1. 读取 `project/<scene>/configs/pipeline.json`，与 `common/pipeline/run_scene.py` 中的默认值合并。
2. 在 `cache/<scene>/pipeline/<run_id>/` 建立试跑目录，写入源码快照，并为既有阶段脚本生成旧格式配置。
3. 按顺序执行阶段：geometry → wind → temperature → temperature3d → pollution → solar → flood →
   plot → verify → visualize。每个阶段在子进程中运行，日志写入 `logs/<stage>.log`，
   状态写入 `pipeline_status.json`；已完成的阶段在复用同一 `--run-id` 时跳过。
4. visualize 完成后，`common.export.package_export` 生成并校验协议 bundle；
   `--retain` 通过 `common.runs.promote_bundle` 复制到 `project/<scene>/runs/` 并注册视图，
   不覆盖已有运行或视图。

geometry 阶段只体素化配置中的现有 GLB（`source`），不重新生成城市模型。

### 实验：`p4d experiment <simulation>`

运行 `urban_flow.scenarios.<simulation>.run`（actuator_lab、windfarm_2m、windfarm_crop、
windfarm_neural），结果写入 `common.runtime.trial_root` 给出的 cache 试跑目录，不自动保留。

### South Kensington 建模

扩展城市模型由 `urban_geometry/agent/` 中的脚本在 Blender 后台模式生成：
`build_expansion.py` 组装，`verify_export.py` 导出并重新导入核对，`render_expansion.py` 渲染。
它们读写 `project/south_ken/geometry/authoring/`，每次使用新的 `--run` 名称，
目前尚未接入 `p4d run`。

### 查看结果

`p4d serve`（默认端口 8769）提供首页和统一查看器
`/src/visualization/viewer/?scene=<scene>&view=<view>`。服务器显式映射配置的 data_root，
支持 HTTP Range 按需读取 NPY；旧专用查看器通过显式映射访问迁移后的资产。

## 数据接口要求

跨模型数据应携带坐标参考系、局部原点、轴方向、数组轴顺序、网格间距、空间范围、
固体掩膜语义、变量单位、时间原点与步长、来源和模型版本。
不能假定所有模型风速符号相同，不能将更新次数直接当作秒。
协议 v1/v1.1 的 manifest 已规定新结果需要声明的字段；历史文件尚未统一补齐元数据或实现自动转换，
重采样、时间插值、风速符号与单位转换属于明确的适配逻辑。

## 检查

`make format-check`、`make lint`、`make test` 和 `make test-e2e` 分别对应 CI 中的格式、lint、
单元测试和 `E2E smoke`；所有改动都必须通过 `E2E smoke`，说明见 [e2e-ci.md](framework/e2e-ci.md)。
CUDA 求解、训练、Blender 建模和真实城市数据的检查需要各自环境，不在 CI 中运行。
