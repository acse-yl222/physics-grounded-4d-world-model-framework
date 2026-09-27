# UrbanWorldModel

> **新模块接入规范（v1）**：[目录与仿真/可视化协议](docs/framework/protocol-v1.md) · [Agent skill](.agents/skills/urban-simulation-contract/SKILL.md)。目标结构为 `src/`、`project/`、`cache/`；旧代码尚未整体迁移。


<p align="center">
  <a href="https://acse-yl222.github.io/urban-world-model/viewer/3d/"><img src="docs/media/hero_south_kensington_uav.jpg" alt="South Kensington: city model with UAV corridors, traffic and stations" width="100%"></a>
</p>

<p align="center">
  <b><a href="https://acse-yl222.github.io/urban-world-model/viewer/3d/">🌐 在线 Demo：South Kensington</a></b> ·
  <b><a href="https://acse-yl222.github.io/urban-world-model/viewer/3d/?scene=white_city">White City 9 km²</a></b> ·
  <a href="https://acse-yl222.github.io/urban-world-model/docs/">项目页</a> ·
  <a href="https://github.com/acse-yl222/urban-world-model">查看器仓库</a>
</p>

城市世界模型：把一个城市片区的三维模型（GLB）变成体素网格，在上面跑风、温度、污染、日照、洪水
五种环境物理场，叠加交通、鸟群、无人机等动态实体，并在网页三维查看器里交互展示。

<table>
  <tr>
    <td width="33%"><a href="https://acse-yl222.github.io/urban-world-model/viewer/3d/?scene=white_city"><img src="docs/media/hero_white_city_wind.jpg" alt="White City wind field"></a><br><sub><b>风场</b> · White City，SCALED 潜空间代理模型，8 m 帧</sub></td>
    <td width="33%"><a href="https://acse-yl222.github.io/urban-world-model/viewer/3d/"><img src="docs/media/geometry_campus.jpg" alt="South Kensington geometry"></a><br><sub><b>几何</b> · South Kensington core008，含 OSM 补充建筑与精修</sub></td>
    <td width="33%"><a href="https://acse-yl222.github.io/urban-world-model/viewer/3d/?pose=campus&shot=junction"><img src="docs/media/traffic_replay.jpg" alt="Traffic replay"></a><br><sub><b>交通</b> · 路网车流回放与信号</sub></td>
  </tr>
  <tr>
    <td><a href="https://acse-yl222.github.io/urban-world-model/viewer/3d/?pose=overhead&phase=solar&solar=shadow"><img src="docs/media/sunlight_shadows_june.jpg" alt="Sunlight shadows"></a><br><sub><b>日照</b> · 夏至日直射阴影，1 m</sub></td>
    <td><a href="https://acse-yl222.github.io/urban-world-model/viewer/3d/?phase=flood"><img src="docs/media/flood_hazard.jpg" alt="Flood hazard"></a><br><sub><b>洪水</b> · 暴雨最大流速与危险度，1 m 浅水方程</sub></td>
    <td><a href="https://acse-yl222.github.io/urban-world-model/viewer/3d/?phase=poll"><img src="docs/media/pollution_step100.jpg" alt="Pollution transport"></a><br><sub><b>污染</b> · 上风差分输运，分层浓度</sub></td>
  </tr>
</table>

仓库只有四类东西：代码（pipelines/）、输入（input/）、输出（output/）、查看器（visualizer/）：

| 目录 | 职责 |
| --- | --- |
| pipelines/ | 全部代码。顶层是场景入口（`run_scene.py` 一条命令跑完整个流程）和各阶段脚本，`paths.py` 解析项目根路径 |
| [pipelines/geometry/](pipelines/geometry/STRUCTURE.md) | 几何代码：GLB 体素化（`voxelization/`）、core008 合并/体素化脚本、鸟群、交通、UAV |
| [pipelines/physics/](pipelines/physics/README.md) | 物理代码：SCALED 潜空间风场（`wind/`）、日照（`solar/`）、洪水（`flood/`）、温度和污染的交付包、core008 历史脚本 |
| [visualizer/](visualizer/README.md) | three.js 网页查看器，独立 git 仓库（GitHub Pages 发布用），按场景读取 `scenes/<id>/` |
| input/ | 你放进来的场景：一个文件夹一个场景，里面是 GLB 和 `config.json` |
| [output/](output/README.md) | 统一资产目录：体素、物理场、中间文件、日志、最终结果 |
| configs/ | 旧的 core008 / white_city 手工配置（保留，`run_scene` 不需要） |
| [docs/architecture.md](docs/architecture.md) | 数据接口要求和迁移状态 |

## 模型与贡献者

| 模型 | 方法 | 代码位置 | 贡献者 |
| --- | --- | --- | --- |
| Urban Geometry Model | GLB 体素化、语义分类、场景合并 | `pipelines/geometry/voxelization/`、`pipelines/geometry/core008/` | Yueyan, Xinyang |
| Traffic Model | 路网车流仿真与预测 | `pipelines/geometry/traffic/` | Xinran, Bohan, Yueyan |
| Bird Model | 鸟群飞行仿真 | `pipelines/geometry/birds/` | Akira, Yueyan |
| UAV Model | 无人机站点选址与航线 | `pipelines/geometry/uav/` | Bohan, Yueyan |
| Wind Flow Model | SCALED 潜空间代理模型 | `pipelines/physics/wind/` | Zhongkai, Yueyan |
| Temperature Model | Neural Physics（三维物理求解器 + 温度代理） | `pipelines/physics/environment-integration/`、`pipelines/physics/wind_temperature_teacher/` | Yiqi Zhu, Zhongkai, Yueyan |
| Pollution Model | Neural Physics（上风差分输运） | `pipelines/physics/wind_pollution_code/` | Yueyan, Yuhang Dai, Zhongkai |
| Flooding Model | Neural Physics（半隐式浅水方程） | `pipelines/physics/flood/` | Yueyan, Dingyu |
| Sunlight Model | Neural Physics（阴影、天空可见度、清空辐照） | `pipelines/physics/solar/` | Yueyan |

场景流程、统一资产目录和网页查看器集成：Yueyan。

**作者（拟定）**：Yueyan Li\*, Zhongkai, Bohan, Akira, Yiqi Zhu, Yuhang Dai, Xinran, Xinyang, Dingyu†, Christopher Pain
（\* 第一作者；† 通讯作者。所有作者均来自 Imperial College London）

## 一条命令跑一个新场景

1. 建一个输入文件夹，放进 GLB 和配置：

   ```text
   input/my_area/
   ├── scene.glb        # glTF 2.0 二进制，Draco 压缩或未压缩都可以；节点变换必须已烘焙
   └── config.json      # 域范围、分辨率、要跑的阶段；没写的键用默认值
   ```

   最小配置只要两行（其余见下面的配置说明）：

   ```json
   { "scene": "my_area", "source": "scene.glb" }
   ```

2. 先看规划，不跑任何东西：

   ```bash
   python -m pipelines.run_scene input/my_area --dry-run
   ```

   它会打印网格大小、按 White City 参考运行折算的粗略耗时和磁盘、每个阶段的状态和将要执行的命令。

3. 跑：

   ```bash
   python -m pipelines.run_scene input/my_area
   ```

   长任务建议放后台：`nohup python -u -m pipelines.run_scene input/my_area > output/my_area/run.log 2>&1 &`。
   进度看 `output/my_area/pipeline_status.json` 和 `output/my_area/logs/<stage>.log`。
   中断后重新执行同一条命令即可：做完的阶段跳过，风场从最后一个检查点续跑。

4. 看结果：

   ```bash
   python visualizer/serve.py            # 打开 http://localhost:8787/viewer/3d/?scene=my_area
   ```

   工作站上对外服务用 `visualizer/start_server.sh`（0.0.0.0:8787，Tailscale 可达）。

现成例子：`input/white_city/` 是 White City 9 km² 的配置，对应的完整结果已在 `output/white_city/`，
`python -m pipelines.run_scene input/white_city --dry-run` 会显示所有阶段均已完成。

## 运行环境

用 `holoscene` 环境（PyTorch 2.7 + CUDA、diffusers、numba、DracoPy、scipy、matplotlib、Pillow 都在）：

```bash
/home/yl222/miniforge3/envs/holoscene/bin/python -m pipelines.run_scene input/my_area
```

风场需要 SCALED 权重仓库 `/home/yl222/workspace/SCALED-Tutorial`（`weight/compression.pth`、`weight/inference.pth`），
温度代理需要 `pipelines/physics/wind_temperature_teacher/weights/temperature_one_step.pt`；路径都可在配置里改。
重建环境时至少安装：torch、diffusers、numpy、numba、DracoPy、scipy、matplotlib、Pillow。

## 配置说明（input/<scene>/config.json）

| 键 | 默认 | 含义 |
| --- | --- | --- |
| `scene` | 文件夹名 | 场景 id，小写字母、数字、下划线；决定 `output/<scene>/` 和 `visualizer/scenes/<scene>/` |
| `source` | `scene.glb` | GLB 文件，相对输入文件夹或绝对路径 |
| `domain.cell_m` | 2 | 网格边长，只能 1、2、4（SCALED 编码器按 256 格分块，风场固定 64 层） |
| `domain.crop_local_m` | null | `[x0, y0, x1, y1]`，局部米坐标，只算这个矩形；null 为整个 GLB。局部坐标 = glTF 的 (x, -z, y)，z 向上 |
| `domain.wind_layers` | 64 | 风场用的底部层数 |
| `georeference.confirmed` | false | 日照和洪水的开关：GLB 没有经纬度和真实地形，必须显式确认按"平地、+y 为北"假设跑 |
| `georeference.latitude_deg` / `longitude_deg` | null | 太阳位置用的经纬度 |
| `stages` | 全部 | 要跑的阶段列表，见下表 |
| `wind.steps` / `step_seconds` | 100 / 50 | 风场步数和每步秒数（50 s 是网格缩放解释，不是校准时钟） |
| `wind.coarse_factor` | 4 | 温度、污染用的粗网格倍数（2 m 场景就是 8 m） |
| `wind.min_free_gib` | 2 | 磁盘余量低于此值停止 |
| `thermal.*` | 26 °C 环境、30 °C 地表/屋顶 | 受控热场景参数（`ambient_c`、`ground_c`、`roof_c`、`temperature_steps` 等） |
| `temperature3d.frames` | 20 | 三维物理温度用最后多少个风场帧驱动 |
| `solar.dates` / `minutes` | 夏至+冬至 / 10 | 日照模拟的日期和帧间隔 |
| `flood.*` | 3 h 暴雨 | 雨量曲线（每 15 min 的 mm/h）、排水、下渗、糙率、时长、帧间隔 |
| `visualize.layer` | 1 | 网页展示哪一层粗网格（1 = 第二层，2 m 场景就是 8–16 m） |
| `visualize.title` | 场景名 | 查看器里的标题 |

## 阶段

| 阶段 | 做什么 | 输出到 `output/<scene>/` | 前置 |
| --- | --- | --- | --- |
| geometry | GLB 体素化：屋顶高度、建筑柱、地面/草地/沥青/铺装/树冠分类 | `geometry/voxel_<cell>m/` | 无 |
| wind | SCALED 潜空间风场，逐步保存粗网格帧和潜场检查点，最后解码整场 | `physics/scaled_latent/wind/` | geometry |
| temperature | 受控热求解器 + 单步温度 U-Net 迁移诊断（粗网格） | `physics/scaled_latent/temperature/` | wind ≥ 10 步 |
| temperature3d | Yi Qi 三维物理温度求解器，受控 26/30 °C 场景 | `physics/temperature3d_physical/` | wind |
| pollution | 假设上游线源的上风差分示踪物输运 | `physics/scaled_latent/pollution/` | wind |
| solar | 阴影、天空可见度、清空辐照度 | `physics/solar_experimental/` | geometry + 确认地理假设 |
| flood | 半隐式浅水方程，GLB 地面当地形 | `physics/flood_experimental/` | geometry + 确认地理假设 |
| plot | 风场、收敛、温度误差、污染总览图 | `physics/scaled_latent/figures/` | wind |
| verify | 文件完整性和数值合理性检查 | `physics/scaled_latent/verification.json` | wind、temperature、pollution、plot |
| visualize | 导出查看器数组、生成 `scene.json`、注册场景、预渲染 PNG 帧 | `visualizer/scenes/<scene>/` | geometry（有哪些结果就导出哪些层） |

前置不满足的阶段会被跳过并在 `pipeline_status.json` 里写明原因，不会报错。
`--stage <name>` 只跑某个阶段，`--force <name>` 强制重跑已完成的阶段。

## 输出布局

```text
output/<scene>/
├── configs/                  run_scene 生成的旧格式配置（scaled_latent.json、surface_physics.json）
├── logs/<stage>.log          每个阶段的完整日志
├── pipeline_status.json      阶段状态、网格规划、耗时
├── geometry/voxel_<cell>m/   体素、掩膜、metadata.json（坐标公式、来源哈希）
└── physics/
    ├── scaled_latent/        wind/、temperature/、pollution/、figures/、run_config.json、verification.json
    ├── temperature3d_physical/
    ├── solar_experimental/
    └── flood_experimental/
```

core008（South Kensington）的历史结果在 [output/core008/physics/](output/core008/physics/README.md)，
由 `pipelines/physics/run_core008_*.py` 系列脚本和 `python -m pipelines.core008` 产生，不经过 `run_scene`。

## 限制

- 风场是 SCALED 代理模型迁移到新几何，没有 CFD 或实测验证；温度是受控场景；污染是假设线源；
  日照和洪水依赖用户确认的经纬度和"GLB 地面当地形"假设。查看器底部会列出这些限制。
- 耗时和磁盘：White City 2 m、1792×1792×64 格、100 步风场在 RTX 5090 上约 2 小时、6 GB。
  1 m 网格是 8 倍格子数；`--dry-run` 会按格子数折算。
- 分类靠 GLB 的节点名和材质名推断（见 `pipelines/geometry/voxelization/prepare_glb.py` 的 `category`），
  命名习惯不同的模型可能把所有东西都当建筑。
- `visualizer/` 是独立 git 仓库，大文件（GLB、npy）被其 `.gitignore` 排除，只有掩膜和 PNG 帧会进版本库。
