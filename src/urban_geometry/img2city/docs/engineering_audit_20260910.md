# 工程规范核查与 AI 配置层重构

2026-09-10。范围：Img2City 工作区（不涉及旧论文仓库）。所有改动只在工作树，没有 commit / push / 改动 index。

## 核查结论

| 项目 | 状态 | 处理 |
|---|---|---|
| 密钥泄露（工作树 + git 历史扫描 AIza/sk-/sk-ant） | 未发现 | — |
| 大文件 / 二进制入库 | 未发现（最大为 vendored maplibre/three） | — |
| 打包（pyproject、package-data、wheel 构建） | 合格 | 版本改为单一来源 `img2city.__version__`（`dynamic`） |
| 依赖锁（requirements-lock.txt） | 合格 | 未改动（ruff 只进 `[dev]` extras，不进锁） |
| lint | 无配置 | 新增 `[tool.ruff]`（pyflakes + 真错误级 pycodestyle），`make lint`，CI 增加 lint 步骤；全仓通过 |
| 测试 | 104 通过 | 现 110 通过（新增 `.env` 解析 / provider 路由 / 端点 / 收据测试） |
| CI | 只跑测试 | 增加 lint、compileall、导入 `agent.llm` / `doctor` |
| `.gitignore` | 缺 `.env.*`、ruff/mypy 缓存 | 补齐（`!.env.example`） |
| 文档与代码不一致 | README 默认模型写 `claude-opus-5`，代码是 `gpt-6-astra`；`--backend sdk` 说明过时 | README / CLAUDE.md / architecture.md 同步 |
| CLI `--out` 默认值 | 25 个阶段各自硬编码 `data/city_sk` / `city_cw` / `city_icl` / `city_sk2` | 统一 `required=True`（编排器本来都显式传 `--out`） |
| 环境变量命名 | `PHOTO_CARD_MODEL`、`ONESHOT_EXEMPLAR` 无前缀、未登记 | 改为 `IMG2CITY_PHOTO_*_MODEL`、`IMG2CITY_ONESHOT_EXEMPLAR`，旧名仍兼容 |
| 真实缺陷（lint 发现） | `library/learn.py` 用了未定义的 `here`（异常被吞，方言词表静默缺失） | 改为 `kit.SPEC_DIALECT_JSON` |
| 未使用导入 / 变量、lambda 赋值 | 30 处 | 清理 |

## AI 配置层（本次主要改动）

问题：模型路由靠模型名前缀判断（`is_astra = model.startswith("gpt-6-astra")`），Anthropic API 调用在 4 个文件里各复制一份，`gpt-image-2` / `gemini-*` / `api.openai.com` 硬编码，配置项名字绑死在 "Astra" 上，`.env.example` 需要手动 `source`。

现在：

- `img2city/config.py` 在导入时自动加载仓库根目录 `.env`（`IMG2CITY_ENV_FILE` 可改路径；shell 已导出的变量优先；`KEY=` 空值视为未设置，不会遮蔽 CLI 登录）。子进程通过 `config.subprocess_env()` 继承。
- provider 与模型分离：`IMG2CITY_LLM_PROVIDER ∈ {codex, openai, claude-sdk, claude-api}`，`IMG2CITY_MODEL` 及各职责 `IMG2CITY_{VISION,SPEC,JUDGE,LEARNING}_MODEL`。模型值可写 `<provider>:<model>` 为单个职责固定 provider（例：`IMG2CITY_JUDGE_MODEL=claude-api:claude-sonnet-5`）。
- 端点 / 二进制：`OPENAI_BASE_URL`、`ANTHROPIC_BASE_URL`、`IMG2CITY_CODEX`、`IMG2CITY_CLAUDE_CLI`；图像编辑模型 `IMG2CITY_IMAGE_EDIT_MODELS`（`openai:` / `gemini:` 前缀，按序尝试）；Overpass 镜像 `IMG2CITY_OVERPASS_URLS`。
- `img2city/agent/llm.py` 是唯一入口：`vision_call(system, user, images, model, backend=...)` 解析 provider（前缀 > `--backend` > `.env`），分发到 `openai_backend.py`（Codex CLI / Responses API）或 `claude_backend.py`（Agent SDK / Messages API），每次调用写收据到 `IMG2CITY_MODEL_LOG_DIR`；`healthcheck` 对所有 provider 统一。
- 删除 `agent/sdk_backend.py`、`agent/astra_backend.py`；`ClaudeAgent`/`SDKAgent` 合并为 `planner.LLMAgent`，`ClaudeVLMCritic`/`SDKCritic` 合并为 `evaluator.LLMCritic`。
- 所有 `--backend` 参数默认 `None`（用 `.env`），可选值为四个 provider 名加 `sdk`/`api` 简写；`city.generate` 的预检 / 限额等待不再只对 `sdk` 生效。
- 旧变量名 `IMG2CITY_ASTRA_BACKEND` / `IMG2CITY_ASTRA_REASONING` / `IMG2CITY_ASTRA_TIMEOUT` 仍被读取（作为回退），建议改用 `IMG2CITY_LLM_PROVIDER` / `IMG2CITY_LLM_REASONING` / `IMG2CITY_LLM_TIMEOUT`。

切换模型：`cp .env.example .env`，改 `IMG2CITY_LLM_PROVIDER` 与 `IMG2CITY_MODEL`（或按职责），`img2city doctor` 查看解析结果。

## 密钥不进 GitHub

- 只有空模板 `.env.example` 入库；`.env`、`.env.*` 全部 git-ignore（`git check-ignore` 已验证）。
- 密钥只在请求参数 / 请求头里使用，没有任何 print、JSON、收据会带出密钥；`doctor` 只显示是否设置。
- 订阅路线（`codex`、`claude-sdk`）不需要任何密钥，只依赖本机 CLI 登录；别人 clone 后 `make env` 建 `.env`，按自己的情况填 provider 或 key。
- `tests/test_repo_hygiene.py`（随 `make test` / CI 运行）检查：`.env` 被忽略、模板里密钥项为空、所有会被提交的文本文件没有 key 形状的字符串（AIza… / sk-… / sk-ant… / gh?_…）。

## 验证

- `python -m ruff check .`：通过。
- `python -m pytest tests`（不含需要本地网站的 site 测试）：110 通过。
- `python -m compileall img2city`、`bash -n scripts/overnight_refine.sh`、CI YAML 解析：通过。
- `pip wheel .`：`img2city-0.1.0` 含 kit/vendor、webapp/ui、typology JSON。
- `IMG2CITY_ENV_FILE` 指向临时 `.env` 后，`doctor` 与阶段子进程均按文件解析 provider / 模型。
- 未做真实模型调用；`claude-api` 路径依赖 `anthropic` 包，本机 mpm2025 未安装。

## 未处理（有意保留）

- `E701/E702/E741`（分号压缩写法）在 `district*.py`、`recover_target.py`、`quality.py` 等新文件和 agent 生成的 `parts_learned.py` 中大量存在，只列为 ruff 忽略项，未重排。
- `docs/*_20260909.md` 为历史工作记录，其中对 `astra_backend.py` 的引用未改写。
- 仓库有大量尚未 `git add` 的新文件（tests、docs、LICENSE、Makefile 等），由你决定提交范围。
