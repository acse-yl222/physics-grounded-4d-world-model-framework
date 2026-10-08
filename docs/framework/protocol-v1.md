# Physics-Grounded 4D World Model Framework 仿真与可视化协议 v1

状态：已实现的接入规范。路径解析、运行保留、场景/视图注册及统一查看器已接通，验证范围见 [实施记录](implementation-status.md)。
协议版本 `1.1.0`（兼容 `1.0.0` JSON 示例）。本文件优先于历史文档。旧根目录已迁入 src/project；历史笔记本的外部依赖与数据需显式提供。

## 阅读说明

本文使用中文说明规则，代码字段、接口名称和路径保留英文，以便与实现对应。

| 术语 | 中文含义 |
| --- | --- |
| scene | 场景：共享空间坐标的一组几何、配置和运行结果 |
| run | 一次仿真运行及其输出 |
| manifest | 运行清单：声明数据、来源、坐标、时间和图层的 JSON 文件 |
| layer | 图层：可单独加载、显示和查询的一组数据 |
| widget | 可视化组件：把图层数据转为几何、箭头、曲线等展示 |
| asset / artifact | 资产文件 / 附加产物，如模型、数组、日志和源码快照 |
| provenance | 来源与复现信息：代码版本、参数、输入和文件校验值 |
| schema | 结构规范：机器可执行的 JSON 校验规则 |
| sampling | 时间采样方式：静态、阶梯取样或线性插值 |
| bundle | 运行集合：一起保留并注册为一个视图的多个运行 |

## 1. 目录与责任

```text
src/
  urban_geometry/          # 3D agent、几何构建、转换
  urban_flow/              # 风、温度、污染、水等求解与导出
  traffic/                 # 交通求解与导出
  visualization/
    viewer/                # 统一查看器入口和布局
    widgets/               # 仿真展示适配器
    shared/                # 相机、时间轴、图例、图层与选择
  common/                  # 协议读写、路径等真正共用的能力
project/<scene>/
  project.json             # 场景身份、坐标与数据索引
  input/                   # 原始输入，不覆盖人工或外部来源数据
  geometry/                # 场景共享几何版本
  configs/<simulation>.json
  runs/<run_id>/           # 经选择保留的运行；不覆盖历史运行
    manifest.json
    data/
  views/<view_id>.json     # 选择哪些运行/图层及初始视角
cache/<scene>/<simulation>/<run_id>/
schemas/
docs/framework/
```

使用单数 `project`。模块和场景名使用小写 snake_case。标准场景 ID 是
`south_ken`、`white_city`；`core008`、`south_kensington` 仅作为旧数据别名，
由迁移适配器显式映射，不直接重命名所有引用。`run_id` 应唯一，推荐 UTC 时间戳加短随机后缀。
新的领域可以新增 `src/<domain>`，不要把所有仿真塞入 `urban_flow`。

一个仿真可以对应多个 widget；一个 widget 也可以被多个仿真复用。
求解器不依赖浏览器，widget 不承担求解。数据导出适配器负责将内部结果变为协议资产。

## 2. 数据位置与保留规则

Git 保存代码、协议、场景配置、视图配置和小型合成示例。大型模型、真实场景结果、
权重和环境不自动进入 Git。目录名称不能代替数据来源和发布许可检查。

本地可选 `storage.local.json`（已加入 Git ignore）：

```json
{"data_root": "/absolute/path/to/urban-data", "cache_root": "/absolute/path/to/scratch"}
```

数据工作区由显式 `--root`、`P4D_ROOT`、兼容变量 `UWM_ROOT`、开发安装的源码根依次选择。
wheel 安装不推测 site-packages 为工作区；需显式指定已有目录。内置 schema、示例和查看器
从程序资源读取，不受工作区或 data_root 影响。
路径解析规则：未配置时以工作区为 data_root，cache_root 为工作区下 cache；
配置后，大数据位于 `<data_root>/project/<scene>/{input,geometry,runs}`，
缓存位于 `<cache_root>/<scene>/<simulation>/<run_id>`。
小型 `project.json`、configs 和 views 始终在仓库内。运行入口必须打印解析后的路径，
不能因缺少外部数据静默切换到另一份数据。解析器位于 `src/common/storage.py`；使用 `p4d paths <scene>` 检查解析结果。

`cache` 必须可删除、可重算。人工修正、唯一原始数据、选定正式结果不应只放在 cache。
清理器只能移除已结束且未被保留的工作目录，不跟随符号链接，不清理活动运行。
试跑转正式结果时，把依赖完整复制/移动到 runs，校验后再写 `complete` manifest；
完成的 manifest 不得引用 cache。失败或运行中的结果不注册到默认视图。

## 3. 场景与视图约定

`project.json` 包含 `schema_version`、`scene_id`、`title`、`spatial` 与 `inputs`。
`spatial` 使用下述 manifest 的同一结构；inputs 记录逻辑路径、来源、版本或 SHA-256、
许可/使用限制。各 run 的空间定义必须与场景一致，或提供显式转换。

views 文件包含 `schema_version`、`scene_id`、`runs`（run ID 列表）、`layers`
（每项指定 run_id、layer_id、visible）及可选 camera（position、target，均为场景坐标）。
跨 run 图层的完整身份是 `(run_id, layer_id)`。不要用“最新修改的目录”隐式选择结果。
project/views 分别由 `project-v1.schema.json`、`view-v1.schema.json` 校验；`common.catalog.view` 同时检查图层引用、场景坐标和绝对时间对齐所需的 epoch。

## 4. 运行清单（manifest）

机器定义见 [JSON Schema](../../schemas/run-manifest-v1.schema.json)，可执行的小型示例见
[manifest](../../examples/contract-v1/manifest.json)。每个运行记录：

- 身份：schema_version、scene_id、simulation、run_id、status、created_at。
- provenance：代码版本、dirty 标志、参数副本、输入标识及 SHA-256。dirty=true 的正式
  科学结果还需保留可恢复的源码补丁或源码快照；版本号本身不足以重现运行。
- spatial：局部坐标原点的经纬高、原点高程基准、场景米制范围。v1 统一右手 ENU，
  x 东、y 北、z 上，单位米；其他坐标系在导出阶段转换。引擎如采用 y-up，在公共层统一转换，
  并同步转换位置、向量、法线和相机。不得只转换几何、不转换流场。
- time：秒制相对时间轴、严格递增且有限的 samples；可选 UTC epoch 用于跨运行对时。
- layers：资产、字段与单位、时间采样方式、展示建议以及支持的交互能力。

每个 layer 的 asset 是 manifest 所在目录内的相对文件路径，禁止绝对路径、URL、`..`
及解析后逃出运行目录的符号链接。浏览器通过部署时设置的 run base URL 访问同一目录结构；
禁止把本机磁盘路径塞进前端 manifest。公开部署必须另外复制被选择的可发布结果。

v1 最小编码是 UTF-8 JSON，`kind` 决定 payload：

| kind | JSON payload | 可视化工具与典型交互 |
| --- | --- | --- |
| mesh | positions: N×3；triangles: M×3 整数索引 | 网格、材质、透明度、对象选择 |
| scalar_field | positions: N×3；values: N 或 T×N | 色带、范围、数值查询；剖切需能力声明 |
| vector_field | positions: N×3；vectors: N×3 或 T×N×3 | 箭头；流线需插值器支持 |
| trajectories | ids: N 个唯一字符串；positions: T×N×3 | 实体、轨迹、回放、实体选择 |
| time_series | values: N 或 T×N，labels: N 个字符串 | 曲线、时间游标、数值查询 |

这里 N 是点/实体/通道数；T 必须等于 time.samples 长度。静态层使用 sampling=static；
动态层使用 step 或 linear；mesh 在此版本仅支持 static。轨迹必须是动态层。
无效或缺失值在 JSON 最小编码中禁止；v1.1 NPY 仅在显式无效掩码覆盖的位置允许非有限值。
静态 run 的 samples 为空；包含动态层的 run 必须提供非空 samples。
动态层在共享时间轴上按自身采样规则显示，超出时间范围时隐藏并标明“无数据”，不能循环补帧。
没有 epoch 的不同 run，只有明确选择相同相对起点才允许同步。

标量/向量图层通过 field 给出名称和物理单位；无量纲使用 `1`。向量分量沿 ENU，
速度例如使用 `m/s`。轨迹坐标使用空间定义中的米。所有数值必须有限。

JSON 示例用于互操作基线，不要求大型生产数组使用 JSON。v1.1 已实现 GLB、NPY、
分帧 NPY 和稀疏轨迹编码，详见第 9 节；其他编码扩展必须同时定义 dtype、shape、轴顺序、
字节序、网格原点/间距/采样中心约定、压缩和分块索引（适用时）。仅填写文件扩展名不够。
未知版本、kind 或 format 要明确报错，不能静默按另一种格式解释。

## 5. 统一可视化组件（widget）接口

接口约定如下。JSON、GLB、NPY、分帧 NPY 与稀疏轨迹已实现；场景注册与多运行对时由统一查看器管理：

```ts
interface Widget {
  load(context: ViewerContext, layer: Layer, signal: AbortSignal): Promise<void>;
  setTime(seconds: number): void;
  setVisible(visible: boolean): void;
  pick(query: PickQuery): Selection | null;
  dispose(): void;
}
```

ViewerContext 由统一查看器提供场景根节点、公共坐标转换、共享相机/时间轴、资产加载器、
图例注册器和 selection 事件通道。PickQuery 包含场景坐标射线及屏幕坐标；Selection
包含 run_id、layer_id、可选 entity_id、场景坐标位置、字段/值/单位。具体引擎类型由
shared 模块统一定义，widget 不自行创建第二个全局相机或计时循环。

manifest 的 widget ID 由查看器中的可信注册表映射到实现，不能动态执行 manifest 指定的脚本。
基础注册 ID 为 mesh、scalar_field、vector_field、trajectories、time_series。
capabilities 可声明 pick、legend、slice、opacity；time 根据 sampling 推导。
查看器只展示已支持的工具。不支持的格式/能力必须提供用户可见错误。

load 失败只隔离该图层；取消时释放已分配资源。setTime/setVisible 在加载完成后调用。
pick 在未命中或不支持时返回 null；dispose 可重复调用，移除监听器、图例及持有的资源，
但不得销毁共享相机或仍被其他 widget 引用的资产。

## 6. 检查、兼容与迁移

```sh
python3 -m pip install -r tools/requirements-contract.txt
python3 tools/check_contract.py examples/contract-v1/manifest.json
```

校验器检查 manifest schema、资产路径、标识唯一性、时间顺序、JSON 数值/数组布局和索引。
它不证明物理结果正确、许可合规或浏览器渲染正确。真实接入另需检验已知点的空间对齐、
物理单位、时间播放/范围、图层显隐、选择和资源释放，并记录执行过的检查。

迁移顺序：先 south_ken 几何 + 一种流场；接上统一查看器；再接 traffic 和 white_city。
每次迁移记录原路径、新路径、调用方更新和可复现的检查。旧目录与嵌套仓库在验证完成前保留。
当前 `output` 和 `input/region` 外部链接已解除，不要自动重建链接。外部只读输入通过忽略的 `sources.local.json` 显式配置。

兼容性：不兼容字段/语义改变升级 major；增加编码或可选能力升级 minor；文字修正升级 patch。
当前 schema 接受 1.0.0 和 1.1.0，扩展需要显式更新 schema、读写端和例子。

## 7. Git 与本地职责

公开仓库保存可复用规范和实现，并不代替本地工作目录、未提交工作或大型数据备份。
根仓库保存统一源码，原三个仓库的历史和未提交补丁保留在本地 `.history/repositories`。
Pages 使用独立 `pages` 分支，以已发布站点为基础加上统一查看器，保留旧演示资源。
本次发布不意味着以后自动允许上传任何新数据。

自动检查配置见 [GitHub Actions 示例](contract-workflow.example.yml)。导入与安装检查使用 `.github/workflows/portability.yml`，覆盖协议、纯 JS、包导入和独立 wheel；
较完整的历史检查模板仍保留在上述示例中。

## 8. 当前可执行入口

从仓库根目录运行（框架开发安装使用 editable 模式）：

```sh
python3 -m pip install -e .
p4d paths south_ken
p4d validate examples/contract-v1/manifest.json
p4d retain /absolute/path/to/completed/trial
p4d serve --port 8769
```

首页地址为 `/`，提供 South Kensington、White City 和风电场入口。本地缺少场景运行目录时，
入口指向对应的公开网页。公开真实场景目前仍使用原专用查看器；它们与统一协议查看器并存。
统一查看器地址为 `/src/visualization/viewer/`，可选择已注册且有数据的本地视图，
也可跳转到公开场景。合成协议示例单独提供，不代表真实场景已全部迁入统一组件。
`p4d` 是推荐命令，原 `uwm` 命令保留兼容。
使用 `?manifest=/project/<scene>/runs/<run_id>/manifest.json` 选择服务器可访问的结果。
`p4d serve` 显式映射配置中的 data_root，支持单段 HTTP Range；不通过前端文件路径直接读取磁盘。
`retain` 校验后复制 manifest 及声明的资产到正式 runs，保留试跑目录，拒绝覆盖同名运行。
单运行 retain 不自动注册视图；bundle retain 同时保留多个运行并注册一个有名字的视图。日志/检查点必须通过 artifacts 显式登记才会复制。

验证入口：

```sh
python3 -m unittest discover -s tests -v
node --test tests/test_viewer.mjs
# 另一个终端运行上面的 HTTP 服务后：
# 需要 puppeteer-core，可用 PUPPETEER_MODULE 指向已有安装的 ESM 入口。
# CHROME_PATH 可指定 Chrome 可执行文件。
node tests/browser_contract.cjs
```

## 9. v1.1 生产数据编码

- **glb / mesh**：资产是自包含 glTF 2.0 二进制容器。encoding.coordinate_frame 为
  `glTF-y-up`，即渲染坐标 `(x, up, -north)`；与场景 ENU 的转换由公共层统一处理。
  glTF 缓冲区/纹理必须内嵌，不接受未声明的外部依赖。支持 Meshopt 与 Draco 解码。
- **npy / scalar_field 或 vector_field**：C-order、小端 `<f2`/`<f4`/`<f8`。
  encoding 明确给出 dtype、shape、axes（YX/CYX/TYX/TCYX）、ENU origin_m、
  spacing_m（dx,dy）、sample_location=cell_center、byte_order=little、compression=none。
  origin 是网格西南角、z 为实际采样层高；位置为 `(x0+(col+.5)*dx,y0+(row+.5)*dy,z)`。
  向量 C 轴固定为 east/north/up。时间维度必须等于 manifest time.samples。
  查看器保留完整数组按帧读取，只对绘制的箭头/点稀疏采样；选择结果报告 display_stride。
- **trajectory_frames / trajectories**：UTF-8 JSON `{frames:[{ids:[...],positions:[[x,y,z],...]}]}`。
  每帧实体数量可变化，ids 是帧内唯一字符串，positions 是 ENU 米。
  帧数与 samples 一致；线性插值按实体 ID 匹配，仅在两帧均存在的实体之间插值。
  离开的实体在下一帧消失，新实体在其首个记录帧出现，禁止补造缺失时间段。

`project/<scene>/views/*.json` 的 time_alignment 必填：relative 表示用户显式选择
共用相对起点；absolute 表示将各动态运行的 epoch 转到同一个 UTC 起点。一个 widget
始终收到该运行自身的相对秒数，图层的完整身份是 run_id + layer_id。

- **npy_frames**：与 NPY 网格同一布局，encoding.shape 给出逻辑完整 T 维度，
  encoding.frame_assets 按 samples 顺序列出文件，每个文件保留形如 `[1,C,Y,X]` 或 `[1,Y,X]`。
  主 asset 为保留的索引/原始元数据 JSON；所有依赖必须在同一运行目录内。
- **地形跟随高度**：可选 height_asset 是 `[Y,X]` 小端浮点 NPY，height_dtype 明确数据类型。
  最终采样高度是 origin_m[2] + height[row,col]，高度与速度均保持原始数据。
- **缺失值掩码**：可选 mask_asset 是 `[Y,X]`、`|u1` NPY；只允许 0/1，
  mask_semantics=`invalid_nonzero`。1 表示无效/固体位置，不绘制或查询；0 的数据必须有限。
  掩码不等于流速零，不能把缺失值填成零后冒充计算结果。
- **非地理实验**：spatial.georeferenced=false 显式表示局部工程坐标；origin 经纬度的 0
  仅为未记录值的占位，不表示真实位于经纬零点，禁止据此叠加地理底图。省略时为 true。
- **附加资产**：artifacts 列出 id、asset、sha256、media_type。dirty=true 且 complete 的运行
  必须含 `source_snapshot`，校验器核对路径和哈希；retain 一并复制。
  导入的历史记录若无法恢复原始运行代码，必须在 provenance 中明确标记不可复现，不能
  把当前适配器的 Git 版本冒充原求解器版本。现有导入器使用 `legacy-unrecorded`。

## 10. 新模块接入流程

1. 在 src 对应领域实现求解器。用 `Storage.scratch` / `trial_root` 分配试跑目录；
   用 `Storage.assets` 获取场景输入，禁止写入源码目录或原始输入目录。
2. 导出 schema 对应的 manifest 与所有资产，记录代码、参数、输入哈希和时空约定。
   先复用五类 widget；若需要新格式，同时实现 schema、校验器、解码器与有效/无效样例。
3. 在 cache 内校验和检查物理结果，选择要保留的运行后 `p4d retain <trial或bundle>`。
   城市管线 visualize 阶段已自动生成 protocol bundle；`p4d run <scene> --retain` 自动保留它。
4. 在 project/<scene>/views 中显式选择运行和图层。bundle 会自动注册新视图；
   不覆盖已有默认视图，不用目录修改时间隐式选择结果。
5. 通过 `p4d serve` 检查坐标、单位、时间、掩码、显隐和选择。公开发布另选可发布资产；
   本地新数据不会因为源码公开就自动上传。

`sources.local.json` 可设置 `legacy_output` 与 `region_input` 的外部绝对路径；
仅用于读取已存在数据，不恢复目录链接。`p4d experiment --python <env/python> <simulation>`
运行 actuator_lab、windfarm_2m、windfarm_crop、windfarm_neural 的迁移入口，结果位于 cache。
实验记录导入见 `src/visualization/adapters/import_experiments.py`；完成标志与数组校验均通过
才注册，原实验文件及专用查看器保持可用。
