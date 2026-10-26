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

## imperial_corridor：image-to-three.js 城市模型（2026-10-25）

- 新场景 `imperial_corridor`：以经纬度 (-0.200473, 51.506427) 为中心的 8 km × 8 km 区域，
  范围 lon -0.258203 ~ -0.142743、lat 51.470494 ~ 51.542360，覆盖帝国理工 South Kensington
  与 White City 校区。几何不复用既有 south_ken / white_city 模型，全部重新生成。
- `src/urban_geometry/image_to_threejs`：从 Overture Maps（2026-10-21.0）下载建筑、道路、
  土地利用、水体、树木与街道设施，用 three.js 生成伦敦风格立面、坡屋顶、道路、公园和水面；
  88 个地标模块按网络参考资料重建并替换 152 个 footprint；`resources/` 资产库提供材质、
  路灯、K6 电话亭、邮筒、公交站、长椅、信号灯、车辆与树种，并按 Overture 点位实例化。
- 运行 `20261025T214135Z_534b69` 已通过 `p4d retain` 保留，五个 GLB 图层（buildings、
  landmarks、ground、trees、street_furniture，Meshopt 压缩后约 78 MB）在统一查看器 5/5 加载。
- 数据语义：未标注高度/屋顶/立面的建筑为估计值，并在场景数据中逐栋标记 `inferred`；
  公园散布树木与道路补充路灯为程序生成；车辆资产未放置（无车辆位置数据）。
  构建环境无法访问图片站点，地标参考来自网页检索文本，近似之处记录在各模块 notes。
- 验证：113 项 Python、23 项 JavaScript、格式/lint 与 E2E smoke 通过。
- 2026-10-26 细化：地标增至 267 个（替换 595 个 footprint），覆盖两校区全部建筑、帝国理工
  医学校区与 8 km 内的博物馆、教堂、车站、桥梁、球场和名宅；88 个原有地标加入真实三维窗框、
  檐口、柱式、穹顶与周边设施。树木改为 6 个树种、街道设施细化，均有高/低两级细节。
  新运行 `20261026T012952Z_f0fc1c` 以视图 `detailed` 保留（设为默认），五图层约 155 MB；
  其中 landmarks 约 925 万三角面（dedup + weld + Meshopt 后 104 MB）。车站与停车场中的
  车辆为示意摆放，不是记录数据。验证：113 项 Python、23 项 JavaScript、格式/lint 与 E2E smoke 通过。
- 2026-10-26 冲突修正与交通：`resolve_conflicts.py` 按建筑立面逐侧收窄车行道和人行道、隐藏穿过建筑的
  路段、为未标注桥梁的跨水路段加护栏、把船屋和水中小型无名 footprint 画成停泊船只、移除或挪开
  落在建筑/水面/车行道上的树。`check_conflicts.py` 复查：建筑压车行道 4459 → 422、建筑在水中
  119 → 14、树木冲突 1379 → 124。新运行 `20261026T023258Z_c188dd` 以视图 `resolved` 保留
  （默认视图，叠加交通图层）。`src/traffic/corridor_sumo` 用 SUMO 1.28 在 Overture 路网上模拟交通，
  运行 `20261026T021606Z_72cdfd`（视图 `traffic_sumo`，900 s 稀疏轨迹）。构建环境无法访问 TfL API，
  本次车辆、出租车与公交需求全部为合成数据，并在 provenance 中标明；信号灯位置为按路口等级的假设。
  统一查看器 6/6 图层加载。
- 2026-10-26 真实交通数据：DfT 道路交通计数（9 个行政区 AADF、分方向 AADF 与 07–19 时人工小时计数，
  OGL v3）与 BODS 公交时刻表 GTFS（Mobility Database 镜像，服务日 2026-06-25；域内 1,311 个站点、
  125 条线路、19,454 班次）。`count_state.py` 按小时（07–19）由计数流量与假设车道/通行能力、
  HCM 信控延误/BPR 估计 324 段计数道路的速度、密度与服务水平；SUMO 中观仿真按 DfT 计数标定
  三个时段（运行 `20261026T043740Z_e64e19`，视图 `traffic_dft`，并入默认视图 `resolved`），
  但拟合较差（GEH<5 仅 14–18%，主干道流量约为观测的 43%），已写入 provenance。公交线路状态为
  仿真估计，超过 25% 站点未到达的线路标为 `model gap`；无实时车辆位置与客流数据。
- 2026-10-26 OSM 路网：`osm_extract.py` 从 AWS Open Data 的 OSM planet ORC（ETag
  `64feb52fbc43f746316a007c518728a8-7743`，2026-10-22；ODbL 1.0，© OpenStreetMap contributors）
  按 stripe 二分查找只读取所需列，提取域外扩 1.5 km 内的 37,161 条车行道路、133,695 个节点与
  1,083 条转向限制；`osm_net.py` 用与 `tfl.Enu` 等价的 eqc 投影导入 netconvert（15,237 个节点
  偏差 ≤ 0.005 m），车道、限速、公交道、信号灯与限制来自 OSM 标签，Hogarth 环岛信号为记录在
  `configs/sumo_patches/` 的补丁。Barnes 经 Putney Bridge 连通（Hammersmith Bridge 在 OSM 中禁行
  机动车）。微观仿真仍逐步拥堵（AM 12,338 次 teleport），故三时段改用带路口控制的中观仿真重跑
  （运行 `20261026T122854Z_d1fc54`，未注册视图）：GEH<5 为 15.1/19.8/12.9%，R² 0.31/0.31/0.24
  （此前 14–18%、≈ 0.05），仿真流量约为观测的 49%；teleport 2,393–3,275（此前约 8,000）。
  公交 `model gap` 由 55 降至 5（AM），Barnes 线路 209/33/378/419/485/533 现可仿真。
  `count_state.json` 323 段中 245 段车道数来自 OSM 标签（`lanes_source`）。
