# UrbanWorldModel 仿真与可视化协议 v1

状态：新接入模块的规范与可校验示例；不是已完成的代码迁移或查看器实现。
协议版本 `1.0.0`。本文件优先于旧文档中的目录规划；旧程序仍按原路径运行，直到逐项迁移。

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

本地可选 `storage.local.json`（应在采用新结构时加入 Git ignore）：

```json
{"data_root": "/absolute/path/to/urban-data", "cache_root": "/absolute/path/to/scratch"}
```

数据路径解析规则：未配置时以仓库根为 data_root，cache_root 为仓库根下 cache；
配置后，大数据位于 `<data_root>/project/<scene>/{input,geometry,runs}`，
缓存位于 `<cache_root>/<scene>/<simulation>/<run_id>`。
小型 `project.json`、configs 和 views 始终在仓库内。运行入口必须打印解析后的路径，
不能因缺少外部数据静默切换到另一份数据。此解析器尚待模块接入时实现。

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
project/views 的自动 schema 校验不属于当前 v1 校验器范围，接入时需要增加对应校验。

## 4. 运行 manifest

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
无效或缺失值在这个最小编码中禁止；需要缺失值掩码时先扩展协议。
静态 run 的 samples 为空；包含动态层的 run 必须提供非空 samples。
动态层在共享时间轴上按自身采样规则显示，超出时间范围时隐藏并标明“无数据”，不能循环补帧。
没有 epoch 的不同 run，只有明确选择相同相对起点才允许同步。

标量/向量图层通过 field 给出名称和物理单位；无量纲使用 `1`。向量分量沿 ENU，
速度例如使用 `m/s`。轨迹坐标使用空间定义中的米。所有数值必须有限。

JSON 示例用于互操作基线，不要求大型生产数组使用 JSON。GLB、分块二进制、纹理或其他
编码可以通过以后版本的 schema 与解码器扩展接入：必须同时定义 dtype、shape、轴顺序、
字节序、网格原点/间距/采样中心约定、压缩和分块索引（适用时）。仅填写文件扩展名不够。
未知版本、kind 或 format 要明确报错，不能静默按另一种格式解释。

## 5. 统一 widget 接口

以下为需要实现的接口约定，并非已提供的运行时 API：

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
当前 `output` 和 `input/region` 外部链接已解除，旧运行入口可能缺失数据；不要自动重建链接。

兼容性：不兼容字段/语义改变升级 major；增加编码或可选能力升级 minor；文字修正升级 patch。
当前 schema 接受且只接受 1.0.0，扩展需要显式更新 schema、读写端和例子。

## 7. Git 与本地职责

公开仓库保存可复用规范和实现，并不代替本地工作目录、未提交工作或大型数据备份。
当前公开仓库仍是旧查看器布局；本规范描述目标布局，未批量搬动旧源文件。
后续整合根仓库时需单独决定嵌套仓库如何保留历史以及 Pages 的部署入口。
本次发布不意味着以后自动允许上传任何新数据。

自动检查配置见 [GitHub Actions 示例](contract-workflow.example.yml)。当前未启用线上 CI；拥有 workflow 写入权限时，可将该文件复制到 `.github/workflows/contract.yml` 并提交。
