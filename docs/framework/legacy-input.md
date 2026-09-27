# input/

一个文件夹一个场景：`input/<scene>/` 放 GLB 和 `config.json`，然后

```bash
python -m pipelines.run_scene input/<scene> --dry-run   # 看规划
python -m pipelines.run_scene input/<scene>             # 跑
```

配置键和阶段说明见项目根目录 README。`white_city/` 是完整示例（GLB 与 `output/white_city/source/` 同一硬链接）。
