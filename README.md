# UrbanWorldModel

城市几何、环境流场、交通仿真与统一可视化工程。代码按领域归入 `src/`，场景数据归入
`project/`，可重算的中间结果归入 `cache/`。

框架与统一查看器已落地，支持 South Kensington、White City、风电场与转子实验。
[协议](docs/framework/protocol-v1.md)与 [skill](.agents/skills/urban-simulation-contract/SKILL.md)
约定后续接入方式；[实施记录](docs/framework/implementation-status.md)列出验证范围。
[公开示例](https://acse-yl222.github.io/urban-world-model/)使用合成数据，
[原城市演示](https://acse-yl222.github.io/urban-world-model/viewer/3d/)保留已发布资源。

## 目录

```text
src/
  urban_geometry/       # 体素化、3D agent、建筑模块、鸟群/UAV 几何
  urban_flow/           # 物理模型、求解器与风场实验
  traffic/              # 交通训练、预测、回放接入
  visualization/        # 统一 viewer、widgets、shared、历史专用查看器
  common/               # 路径、协议、场景目录、运行管线、HTTP 服务
project/
  south_ken/            # South Kensington
  white_city/           # White City
  windfarm/             # 不同风电场实验各自保留为 runs
  actuator_lab/         # 转子对照实验
cache/                  # 中间产物和本地依赖环境，不应保存唯一数据
schemas/                # 运行、场景及视图协议
```

`.history/` 是本次迁移保留的原仓库历史与工作区记录，属于本地恢复材料，不能当缓存删除。
它和大场景数据均不自动上传 GitHub。旧版项目介绍与贡献记录保留在
[历史 README](docs/history/README-before-framework.md)和 [Contribution.md](Contribution.md)。

## 启动

使用已有 Python 环境可运行 `python -m pip install -e .`，或用 uv 建立独立环境：

```sh
uv venv cache/framework/venv
uv pip install --python cache/framework/venv/bin/python -e .
source cache/framework/venv/bin/activate
uwm scenes
uwm paths south_ken
uwm serve --port 8769
```

浏览器打开 `http://127.0.0.1:8769/`，可选择场景与视图。GLB 和完整 NPY 帧由同一查看器加载；
NPY 使用 HTTP Range 按需读取，箭头只稀疏绘制，源数组不会被降采样覆盖。
直接用普通静态服务器时，NPY 服务端范围读取可能不可用，应使用 `uwm serve`。

South Kensington 的交通视图使用保存下来的 **1–300 秒**回放；元数据提及的 3,600 秒完整
仿真不等于本地拥有全部帧。多运行视图显式设置相对或绝对时间对齐，超时图层显示无数据。

## 运行与保留结果

```sh
uwm run white_city --dry-run
uwm run --python /path/to/solver/environment/bin/python white_city --run-id my_trial --retain
uwm validate /path/to/trial/manifest.json
uwm retain /path/to/completed/trial
```

`run` 的中间结果位于 `cache/<scene>/pipeline/<run_id>/`；`retain` 仅接受完整、通过协议
校验的运行，复制到 `project/<scene>/runs/<run_id>/` 并拒绝覆盖同名历史结果。
城市管线的 visualize 阶段会生成 protocol bundle；加 `--retain` 即保留结果并注册视图。
单次 `uwm retain` 也可接受这个 bundle。任意历史目录需先导出协议，不能直接当作有效 trial。
大型真实数据保留在本地；克隆公开代码仓库不等于恢复这些数据。

## 后续接入

先阅读 [仿真与可视化协议](docs/framework/protocol-v1.md)，再使用
[urban-simulation-contract skill](.agents/skills/urban-simulation-contract/SKILL.md)。
[AGENTS.md](AGENTS.md) 指引后续 agent 遵循这些约定。

```sh
python -m unittest discover -s tests -v
node --test tests/test_viewer.mjs
uwm validate examples/contract-v1/manifest.json
```

浏览器测试与 GPU/Blender 迁移检查的执行证据见实施记录。

## 本地与 GitHub

`main` 保存源码、协议、配置和小样例，`pages` 保存静态示例及已经公开的旧网页资源。
新克隆没有本地场景数据时，`uwm serve` 默认打开合成示例。真实仿真还需要输入模型、权重、
领域依赖和相应算力。GPU、Blender 与历史笔记本环境不会由基础框架安装自动提供。

本地源码提交并推送后可重新克隆，但 project 中未发布的数据、/data 原件、.history 中的
原仓库恢复材料仍需单独备份。不要把整个本地目录当缓存删掉。
