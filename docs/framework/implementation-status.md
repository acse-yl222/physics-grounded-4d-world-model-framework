# 框架实施与验证记录

2026-09-27：统一源码、场景目录、可删除缓存、版本化协议和仓库 skill 已实现。
公开源码分支为 main，静态站点使用 pages 分支；后者保留原站点已经公开的资产和路由。

## 实现范围

- 可复用代码归入 src/urban_geometry、urban_flow、traffic、visualization 与 common。
  3D agent 在 urban_geometry/agent；权重和场景输入从 src 移入 project/south_ken/input。
- 原 pipelines、input、configs、expansion、visualizer 根目录已迁移。
  output 与 input/region 外部链接未恢复，/data 原始数据未移动或删除。
- `uwm run <scene>` 使用唯一 cache 运行目录；visualize 生成带源码快照的协议 bundle；
  `--retain` / `uwm retain <bundle>` 校验并复制正式运行，然后注册有名字的视图。
  不覆盖同名结果或已有视图。单运行 retain 同样可用。
- 统一查看器管理场景、视图、相机、时间、选择、显隐、透明度和图例。
  五类 JSON 基础图层之外，支持 GLB、完整/分帧 NPY、地形高度、显式无效掩码、稀疏轨迹。
  原始数组保持不变，绘制稀疏箭头不等于数据降采样。
- South Kensington、White City 的真实 GLB 和完整风场已注册；South Kensington 的
  traffic 视图使用原 SUMO 记录 1–300 秒，没有补造未保存的 3,600 秒回放。
- windfarm 与 actuator_lab 已导入 12 个已完成的实验。原实验目录保留；新增协议运行
  通过硬链接复用不变数组，所有运行依赖完整处于各自目录内。
  np4m_legacy_opentop 未完成，保留但不注册。详见 experiment-import.json。
- 历史专用查看器通过 uwm serve 的显式映射访问迁移后的资产。原公开演示仍保留在
  pages 分支；公开统一示例只使用小型合成数据，不上传本地真实场景数据。

## 已执行验证

- 40 项 Python 检查通过：schema、路径隔离、HTTP Range、数据编码、时间与空间、
  artifact 校验、禁止覆盖、bundle 导出→保留→注册，以及太阳辐照日期/UTC 时间。
- 5 项 JavaScript 检查通过：ENU 往返、时间插值/越界、静态时间、资产路径、稀疏实体生命周期。
- 合成示例浏览器：5/5 图层，选择、插值、超时隐藏与资源释放通过，无页面错误。
- 真实城市浏览器：South Kensington 3/3 图层；100 秒 1,498 辆车，抽查 ID/位置与原
  traffic_flow.f32 完全一致；风场插值与 NPY 原值一致。White City 模型与风场加载通过。
- 风电场/转子浏览器：分别抽查 3 秒、1.25 秒，速度插值和地形跟随位置与原 NPY 一致。
- Blender：98 个独立建筑模块导入通过，覆盖 1,128 条建筑映射；另外实际构建并导出
  queens_gate_28，得到 5 个 mesh、1,600 个面及有效 GLB。
- CUDA：MAC 均匀流/投影/固体测试通过；投影散度约 3.95e-7；转子后端投影差
  5.96e-8、平流差 2.98e-8，力守恒误差为 0。
- editable 安装和 `uwm run white_city --dry-run` 通过，输出指向 cache。
- 从最终提交建立无场景数据的干净检出，40 项 Python 检查和浏览器 5/5 图层测试再次通过。
  无本地数据时自动显示合成示例，所需 vendored 浏览器运行时已纳入版本控制。

## 数据保留和清理

- layout-migration.json、scene-migration.json、viewer-migration.json 和 model-migration.json
  保存移动证据。后续代码/配置路径修正不会保留原代码哈希，但数据文件必须保持原值。
- 最终核对 3,055 条场景记录、上游新增的 43 个文件与移动权重；无数据丢失问题。
  详见 final-data-audit.json；未提交的原仓库改动保留在 .history/repositories 中。
- .history 保存原三个仓库的 Git 数据、bundle、HEAD、remote、status 与工作区补丁，
  以及从旧 cache 发现的独有研究输入/代码。它是本地恢复材料，不能当缓存删除。
- 用户授权清理后，删除可重建的旧环境、依赖、字节码，以及确认解压后与保留 GLB
  哈希完全相同的 gzip 副本；发布和干净检出检查完成后移除临时 worktree，累计释放约 1.19 GB。逐项记录见 cleanup.json。
- 原始模型、保留的仿真、源文件和 /data 原件没有作为缓存删除。后续需要另行备份。

## 验证边界与使用要求

- 框架基础安装不包含 Torch/CUDA、Blender 和各历史研究环境。运行对应求解器时需指定
  已安装依赖的 Python。历史笔记本/一次性研究脚本保留原实验语义，其外部资料需自行提供；
  统一入口是 uwm，不能假定任意历史脚本都能在仅有基础依赖的新克隆中运行。
- 没有在本次结构迁移中重跑整个城市的全部耗时仿真，也没有完整重建 1,128 栋城市模型。
  验证覆盖路径、模块导入、代表性构建、现有完整数据和求解器数值回归。
- 老实验未记录原运行 Git 版本，导入 manifest 明确标记 legacy-unrecorded，不声称可严格重现。
  风电场和转子实验未提供地理原点，使用 georeferenced=false 的局部工程坐标。
- GitHub 凭据没有 workflow 写权限，协议测试的 Actions CI 尚未启用（Pages 自带部署任务正常启用）；仅保留
  contract-workflow.example.yml。上述检查已在本地实际运行。
- `cache/framework/browser` 保存本地浏览器报告和截图，可在查看后删除；不会公开提交。
  公开部署由 tools/build_public_site.py 选择静态资产，不复制 project 数据或本地配置。

## 2026-10-08 导入与工作区路径统一

- 公共鸟类、交通和流场入口使用完整包名；直接源码脚本仅在作为主程序时添加 src。
  本轮不改写冻结的上游研究源码或无关历史工具的实验语义。
- `P4D_ROOT`（兼容 `UWM_ROOT`）指定工作区，Storage 管理 data_root/cache_root；
  代码路径和内置资源独立解析。sources.local.json 默认来源遵循 data_root。
- wheel/sdist 包含 canonical schemas、合成示例与静态查看器；独立安装可校验运行、
  在显式空工作区启动查看器。真实仿真仍需对应数据、权重、CUDA/Blender/外部依赖。
- 新增 portability.yml：Python 3.11/3.12 基础检查、纯 JS、独立 wheel，以及 CPU 的领域包导入。
  工作流实际远端执行结果以 PR 检查为准，不以本地检查冒充线上完成。
- 本地检查：55 项 Python 测试、14 项 JS 测试、v1/v1.1 协议示例通过；
  独立 wheel 的 schema、静态 HTTP、源码快照检查通过；wheel 浏览器合成示例 5/5 图层，
  选择、插值、越界隐藏与重复释放通过。转子后端/力守恒、开顶投影检查通过。
  固定种子的 16 鸟三步状态与两条交通轨迹样本在迁移前后 SHA-256 完全一致。
- 对最终改动做了一轮 review，修复目录 index.html 符号链接越界、安装后快照扫描范围、
  渲染器写入输入目录、场景别名/切换缓存根后试跑身份、CPU 导入时依赖 Triton 等问题；
  补充对应回归检查。源码快照保留本项目求解器、导出器和查看器，不扫描其他安装依赖。
- 未合并或部署站点；原工作区未提交的复现改动、数据和恢复材料未包含在此变更中。
