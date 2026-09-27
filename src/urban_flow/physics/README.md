# Physics model：环境物理场

| 领域 | 实现与运行入口 |
| --- | --- |
| 太阳辐射 | solar/model.py；run_core008_solar.py |
| 洪水 | flood/model.py；run_core008_flood_swe.py |
| 风场 | wind_temperature_teacher/code/wind_core.py；run_core008_scaled_latent*.py |
| 多场景潜空间风场 | wind/scaled_latent.py；../scene_scaled_latent.py（run_scene 调用） |
| 温度 | environment-integration/members/yiqi_temperature/；run_core008_temperature*.py |
| 污染 | wind_pollution_code/code/vendor/yuhang/；run_core008_pollution*.py |
| 耦合 | wind_temperature_teacher/code/cloud_workflow.py、wind_pollution_code/code/workflow.py 与场景脚本 |

太阳与洪水核心实现已按领域分包，solar_np.py、flood_swe.py 保留兼容导入。
其他交付包维持原位，保留内部依赖与来源记录。
新入口：项目根目录运行 python -m pipelines.core008 --dry-run --stage all。
[MODEL_INVENTORY.md](MODEL_INVENTORY.md) 是历史盘点，不表示当前任务状态。
