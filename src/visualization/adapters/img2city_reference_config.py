"""Local Img2City display adapter step. See docs/framework/img2city-full-viewer.md. No Git operations."""
import argparse
from pathlib import Path
_parser=argparse.ArgumentParser()
_parser.add_argument('--root',type=Path,default=Path.cwd())
_args=_parser.parse_args()
_ROOT=_args.root.resolve()
from pathlib import Path
import json,shutil
root=_ROOT;run=root/'project/south_ken/runs/img2city_original_page_20261005';p=run/'physics'
scene=json.loads((run/'scene.json').read_text());old=json.loads((_ROOT/'project/south_ken/runs/img2city_original_page_20261005/reference_source/scene.json').read_text());meta=json.loads((_ROOT/'project/south_ken/runs/img2city_original_page_20261005/reference_source/physics.json').read_text());local=json.loads((p/'manifest.json').read_text())
meta['arrays'].update(local['arrays']);(p/'manifest.json').write_text(json.dumps(meta,indent=2))
index=json.loads((_ROOT/'project/south_ken/runs/img2city_original_page_20261005/reference_source/frames.json').read_text());index['layers']={k:v for k,v in index['layers'].items() if not k.startswith(('solar_','shadow_'))}
for v in index['layers'].values():v['shape_yx']=[scene['grid']['rows'],scene['grid']['cols']];v['note']+='; original run cropped to Img2City region, NOT recomputed'
(p/'web/index.json').write_text(json.dumps(index,indent=2))
for key in ['wind','temp','poll','flood','diurnal']:
 scene['layers'][key]=old['layers'][key];scene['layers'][key]['label']+=' · 原版参考';scene['layers'][key]['title']+=' · NOT recomputed for Img2City'
scene['timeline']=old['timeline'];scene['phase_order']=old['phase_order'];scene['masks']=old['masks'];scene['replay']='demo_rev02';scene['replay_base']='replay/';scene['unavailable_modules']=[]
scene['title']='Img2City · South Kensington · 完整演示'
scene['integration_note']='你的 Img2City 地理模型｜日照：本机重算｜风、温度、污染、积水、交通及 UAV：原版参考回放，未针对新建筑重算。'
scene['limits']+=['参考场按项目 region↔campus 矩阵对齐裁切，没有改变原场的物理结果；可能与新建筑冲突。','交通为原版已保存的 300 秒样本；UAV 为原调度演示，未重新做避障。','相机、流线粒子、等温线、日期、昼夜温度、洪水、车辆、信号灯、UAV、鸟群控制沿用原版。']
(run/'scene.json').write_text(json.dumps(scene,indent=2,ensure_ascii=False)+'\n')
for name in ['actors/pigeon.glb','assets/hexacopter_cargo.glb']:
 dst=run/'replay'/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/'src/visualization/legacy/agents/demo_rev02'/name,dst)
print('Attached reference fields and replay configuration')
