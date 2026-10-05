# Astra 接入与南肯地区重生成耗时估算

2026-09-09。已按用户确认，在当前 Img2City 源码启用 Astra。旧论文仓库只读，没有 commit、push 或 GitHub 上传；没有启动整区重跑。本轮小规模实测使用独立目录。

## 已接入的职责

| 职责 | 入口 | 默认配置 |
|---|---|---|
| 类型识别、选景、清图后的视觉验证、庭院/屋顶空间理解、玻璃/店面属性 | building.typology、courtyard_agent、glass_agent、imagery.acquire_view/facade_clean、scene.shop_agent | IMG2CITY_VISION_MODEL |
| 规格生成、自修复、精修、参数规划 | building.generate、city.generate、agent.planner/harness、webapp.photo | IMG2CITY_SPEC_MODEL |
| 视觉评审、成对比较、失败需求回填 | judge.evaluator、SDKCritic、checklist 调用、library.learn | 默认均为 Astra；原强模型 inspector 仍沿用生成模型，pairwise 使用 IMG2CITY_JUDGE_MODEL |
| 新零件提议与实现 | library.grow | IMG2CITY_LEARNING_MODEL |

这些配置均默认 `gpt-6-astra`，总开关为 `IMG2CITY_MODEL`。显式传入 Claude 模型仍可运行原后端；不会在 Astra 失败时自动切回 Claude。`city.make_city` 和夜间精修脚本也已更新，子进程沿用当前 Python 环境。

Blender、OSM、几何计算、确定性测色、ResNet 先验、DreamSim、深度估计和需求文本挖掘没有替换为 LLM。Gemini 的实际图像生成/编辑保持原实现，视觉检查调用已接入 Astra。

## 接入方式和边界

- 默认 `IMG2CITY_ASTRA_BACKEND=codex`、`IMG2CITY_ASTRA_REASONING=high`，调用本机 Codex 登录。
- `agent/astra_backend.py` 只返回模型文本，项目仍负责解析、校验、学习、构建、评分和接受/拒绝。模型调用在独立临时目录、只读沙箱运行，不接管项目流水线。
- 每次成功调用保存请求模型、实际调用路线、耗时、token 用量、输入图片校验值及模型输出。日志在 `IMG2CITY_MODEL_LOG_DIR`，默认 `runs/model_calls/`。没有将订阅用量伪造为美元费用。
- 图片直接以附件提供，Astra 路径不再先缩至旧 Claude 路径的 640px。
- API 调用仅在显式设置 `IMG2CITY_ASTRA_BACKEND=openai` 并提供 API key 时启用，使用 Responses API。此次实测使用 Codex 路线。Astra 标识和 API 参数依据 [OpenAI 官方指南](https://developers.openai.com/api/docs/guides/latest-model)。

实测发现并修正了两项对接问题：旧 imagery gate 将棚下照片一律当室内拒绝，现在允许以卫星轮廓及目标身份交叉验证半开放结构；Astra 会生成不存在的材质名，现在向模型提供真实 kit 材质表，并将校验错误交回 agent 自修复。没有手写车站几何或代填规格。捕获到的零件构建失败也不再被当成完整模型成功。

## 验证结果

- 75 项离线测试通过，覆盖原回归测试以及 Astra 路由、订阅调用参数、图片附件、usage、失败输出拒绝、旧 API 风格 planner/critic 的路由、材质词汇约束。
- Python 源码解析、修改的 JS 语法检查、夜间脚本语法检查、diff whitespace 检查通过。
- AST 扫描未发现仍硬编码 Claude 的可执行模型默认值；历史说明及显式旧后端兼容代码保留。
- 实际调用 `typology.pick → city.agent_spec → gen_spec` 测试普通建筑和南肯站体，另测了 Astra checklist 评分。
- 车站规格先经历项目自修复，再通过真实 Blender kit 构建，输出约 1.1 MB GLB；此文件是小规模构建验证，尚未经过完整视觉精修，不是最终车站交付。
- 没有执行新零件学习门禁、全城视觉回归或实时 Blender MCP 的长时运行测试。独立 Blender 成功不等同于交互式 MCP 已验证。

证据位于 `runs/astra_migration_20260909/`：`unit.log`、`default_audit.json`、`benchmark.json`、`benchmark_station_retry.json`、`repair_probe.json` 和 `model_calls/`。首次车站拒绝及后续修正记录均保留，不隐藏失败尝试。

## 南肯地区规模

以旧仓库 `data/city_sk/buildings.json` 的同一范围为准：

- 252 栋建筑，252 份规格，252 组街景/卫星图。
- 201 栋面积至少 60㎡；77 栋面积至少 200㎡。
- 210 栋有历史精修结果，历史迭代中位数为 3。
- 237 个店面单元；店面/材质调用是否重做取决于重生成范围。
- 现有 checklist 在提供法线图时通常分为街景、俯视、几何三个评审组。默认 inspector_k=3，因此每轮通常需要 9 次 VLM 判断，而非只有一次模型调用。

## 实测耗时与估算

| 小测试 | 实测 |
|---|---:|
| 普通建筑类型卡 | 7.7 秒 |
| 普通建筑初始规格 | 30.4 秒 |
| 车站类型卡 | 6.3–6.7 秒 |
| 车站规格及一次结构校验自修复 | 70.5 秒 |
| 两视图评审，k=1 | 22.0 秒，包含两次模型调用 |
| 额外材质自修复 | 25.4 秒 |
| 车站规格实际构建/GLB 导出 | 6.9 秒 |

以下是小样本外推，不是完整任务实测。假设复用已缓存的真实照片、OSM、道路等数据，使用 mpm2025 环境，模型并发可持续、Blender 可用、订阅额度不打断运行。

| 重生成范围 | 预留墙钟时间 |
|---|---:|
| 252 栋重写初始规格，组装并导出整区，不进行多轮精修 | 约 1–2 小时 |
| 上述整区初稿 + 约 201 栋主要建筑各做 3 轮评审/精修 | 约 4–8 小时 |
| 将小建筑也纳入、增加到 5–6 轮、加强店面与材质复核 | 约 8–16 小时 |

推算依据：初稿模型调用约 30–70 秒/栋，规格阶段配置 3 个并发；类型卡和场景阶段另计。3 轮精修通常含约 27 次分组评审、2 次规格更新、checklist 生成及可能的 A/B 比较/自修复，单栋约数分钟，配置 8 个并发；实际 Blender 构建/渲染共享一个队列，因此不能简单将总时间除以 8。估算留出了重试、修复、导出及并发效率损失的余量。

新零件学习扩库的循环次数取决于未满足需求，且每轮包含跨区域构建回归，不宜提前塞进一个固定时长；上表不包含不限次数的扩库。重新抓取全部街景或重算所有检测缓存也可能额外增加时间。订阅剩余额度不能直接换算为可完成的建筑数；若触发限额，日历耗时还会包括等待恢复。

建议首次整区运行采用“252 栋初稿 + 201 栋、3 轮精修”，预留一晚 8 小时，并在前 10 栋完成后用实际总耗时修正预测。所有重生成结果应进入新的区域目录，避免旧 `spec.json`、`typology.json`、`refine/result.json` 被可恢复执行逻辑误判为新模型已完成。
