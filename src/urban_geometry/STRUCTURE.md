# Geometry model：场景与动态实体

| 逻辑模块                   | 当前实现                                                          |
| -------------------------- | ----------------------------------------------------------------- |
| 静态城市：建筑、道路、树木 | ../expansion/src/                                                 |
| 场景合并                   | geometry/south_kensington_core008_merge.py                        |
| 体素化                     | geometry/voxelize_core008.py、validate_padded_voxels.py           |
| Draco GLB 场景适配         | voxelization/prepare_glb.py；支持烘焙变换的场景，1/2/4 m 格心采样 |
| 鸟群                       | birds/、geometry/birds/                                           |
| 交通                       | traffic/、geometry/traffic/                                       |
| UAV 外形、站点、调度       | uav/、geometry/uav/、mfmu-uwm-integration-preview/                |
| 原集成入口                 | integrate.py                                                      |

静态建模逻辑归入 geometry；expansion 暂保留物理位置，维持 Blender 工程和快照引用。
geometry/ 仍混有输入资产与适配脚本，后续逐项拆分。
原集成入口说明见 [README.md](README.md)，从 pipelines/geometry/ 运行。
鸟群、交通和 UAV 同属动态实体，但共享目录不代表坐标已对齐。
