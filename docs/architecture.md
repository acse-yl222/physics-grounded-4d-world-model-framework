# 框架边界与迁移状态

## 职责

pipelines/geometry 提供静态场景、动态实体轨迹和计算网格。
pipelines/physics 消费网格、初始与边界条件，产生环境物理场。
pipelines 选择配置并调用模型；shared 提供共用基础设施。
重采样、时间插值、风速符号与单位转换属于明确的适配/耦合逻辑。

## 数据接口要求

跨模型数据应携带坐标参考系、局部原点、轴方向、数组轴顺序、网格间距、空间范围、
固体掩膜语义、变量单位、时间原点与步长、来源和模型版本。
不能假定所有模型风速符号相同，不能将更新次数直接当作秒。
这些是后续适配要求，历史文件尚未统一补齐元数据或实现自动转换。

## 本次完成

- 项目总 README 和两大模块导航。
- 太阳/洪水核心实现迁入领域子包，保留旧导入入口。
- shared 路径解析和可预览命令的 core008 太阳运行/绘图入口。
- 日期、时间间隔、小时输出开关和输出目录提取为 JSON 配置。
- 新太阳流程使用 output/core008/physics/solar。
- 2026-09-17：core008 物理结果整体迁入 output/core008/physics/（scaled_latent、scaled_latent_1024、
  digit_smoke、web2d 及总览 README），pipelines/physics 脚本、configs、文档与结果内的 manifest/README 路径同步改写。
  旧路径 physics_model_result/、result/scaled_latent_2d、pipelines/physics/outputs/core008_digit_smoke
  保留为指向新位置的符号链接，仅作兼容，新代码不得再引用。

## 代码全部并入 pipelines/（2026-09-17）

pipelines/geometry/（原 geometry_model/ 的代码：voxelization、core008 合并/体素化脚本、birds、traffic、uav、integrate.py）
和 pipelines/physics/（原 physics_model/ 全部内容，含交付包和权重）；pipelines/paths.py 取代 shared/。
core008 几何数据迁到 output/core008/geometry/，鸟群/交通/UAV 的 core008 数据及其一次性脚本迁到 output/core008/entities/。
physics_model_result、result/ 兼容链接已删除。geometry_model 曾是嵌套 git 仓库（uwm-group1），其 .git 随代码移到 pipelines/geometry/.git。

## 场景入口 pipelines/run_scene.py（2026-09-17）

input/<scene>/config.json 描述来源 GLB、域裁剪、分辨率、地理假设和阶段列表；run_scene 生成
output/<scene>/configs/ 下的旧格式配置，按顺序调用既有场景脚本（prepare_glb、scene_scaled_latent、
scene_temperature_physical、scene_pollution、scene_surface_physics、plot_scene、verify_scene_results），
最后由 pipelines/export_scene_web.py 导出到 visualizer/scenes/<scene>/ 并注册。阶段幂等、可断点续跑，
状态写在 output/<scene>/pipeline_status.json。物理方程和求解器代码未改；prepare_glb 新增 --crop、
--min-layers 和未压缩 glTF 读取。

## 统一资产目录 output/

所有模型代码之外的资产统一归入项目根目录 output/，包括输入资产、生成几何、
计算网格、风场中间文件、模型权重和最终结果。模型从这里读取资产，也向这里写入资产。
不再规划独立的顶层 data/、checkpoints/、cache/、outputs/ 作为资产存储根。

内部按场景和用途组织，不按文件扩展名拆分：一个模型的一组 npy、json 与预览图可以放在一起。
共享权重放 output/checkpoints/；场景资产放 output/<scene>/geometry/；物理场及其中间状态放
output/<scene>/physics/<model>/。需要多次实验时再在模型目录下加实验名。
具体示例见 ../output/README.md。

这是目标目录约定。物理结果（原 physics_model_result、result、pipelines/physics/outputs）已于 2026-09-17 迁入
output/core008/physics/。output/core008/geometry、cache 与交付包中的几何资产尚未搬迁；
迁移时需要同步修改读取路径及缓存路径，保留来源和实验对应关系。

## 后续迁移

- expansion 源码与大型资产分离，修复 Blender 路径后归入 pipelines/geometry/scene。
- 鸟群、交通、UAV 的运行接口和坐标统一。
- 风/温度/污染交付包拆分，保留来源记录与依赖环境。
- 太阳输入路径与坐标常量仍在旧脚本，required_inputs 仅预检，不重定向输入。
- 其他流程接入配置后逐项验证，再集中数据和权重。

此次未改变物理方程。历史导出快照不作为源代码迁移对象。
