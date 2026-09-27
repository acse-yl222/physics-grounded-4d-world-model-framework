# White City

`project.json`、`configs/` 与 `views/` 随源码版本控制。
`input/`、`geometry/`、`runs/` 的本地数据默认忽略；克隆源码不包含这些数据。
运行 `uwm paths white_city` 查看解析路径，使用 `uwm serve` 打开已有场景。
新结果先在 cache 校验，再通过 `uwm retain` 保留。
