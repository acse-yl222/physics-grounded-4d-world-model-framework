"""Package native-resolution offline presentation as four standard ZIP files."""
from pathlib import Path
import argparse,hashlib,json,zipfile
p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('destination',type=Path);p.add_argument('--only-viewer',action='store_true');a=p.parse_args();a.destination.mkdir(parents=True,exist_ok=True)
root='imperial-corridor-native';names=['01-viewer-and-geometry.zip','02-fields-4m.zip','03-wind-history-a.zip','04-wind-history-b.zip'];groups=[[] for _ in names]
selected={'agents','scenes','src','tiles','vendor','viewer','serve.py','start_windows.bat','start_linux.sh','start_mac.command'}
for f in sorted(a.source.rglob('*')):
 if not f.is_file() or f.relative_to(a.source).parts[0] not in selected:continue
 rel=f.relative_to(a.source).as_posix()
 if '/physics/chunks/wind_history/' in rel:g=2 if int(f.stem)<151 else 3
 elif '/physics/' in rel:g=1
 else:g=0
 groups[g].append((f,rel))
readme='''Imperial Corridor — 原始网格离线查看器

全部四个 ZIP 解压到同一目录，会合并为 imperial-corridor-native 文件夹。
01 + 02 包含完整建筑、地表、交通及 4 m 物理场；03 + 04 补齐 8 m 风场时序。
也可运行下载页的 download_all.py，自动下载校验并解压四个包。

需要 Python 3 和支持 WebGL 的桌面浏览器。无需 pip 安装依赖。
Windows：双击 start_windows.bat。
macOS：终端运行 bash start_mac.command。
Linux：终端运行 bash start_linux.sh。
或进入解压目录运行 python3 serve.py（Windows: py -3 serve.py）。
浏览器自动打开，保持终端运行；加载数据不需要互联网。不要直接双击 HTML。

默认风场：4 m 末帧，模型 t = 7500 s，高度 6 m。
Ground & recorded traffic 面板可切换 8 m 风场时间序列（需 03+04）。
日照/阴影、污染、洪水：4 m 原始保存网格；温度：32 m，采样高度 8 m。
保留源数组数值，使用无损 gzip 分帧传输，没有空间插值或图片量化。

地面：4 m 道路/绿地/水体底图，可切换高程着色。按平坦化建筑坐标投影，不表示桥面高差。
交通：点击 Play traffic，播放已保存的 08:50:00–08:59:59 SUMO 早高峰车辆子集。
交通不是实测数据，各物理场及交通使用独立时钟，不表示同步耦合仿真。
建筑为全部 64 个详细瓦片与 267 个地标，约 1161 万三角面。建议桌面电脑。
不含求解器检查点、训练文件、未保存的 4 m 风场中间帧或高分辨率温度仿真。
'''
assets=[]
for name,files in zip(names,groups):
 target=a.destination/name;records=[]
 if a.only_viewer and name!=names[0]:
  with target.open('rb') as h:sha=hashlib.file_digest(h,'sha256').hexdigest()
  assets.append({'name':name,'bytes':target.stat().st_size,'sha256':sha});continue
 with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z:
  for f,rel in files:
   z.write(f,root+'/'+rel,compress_type=zipfile.ZIP_STORED if f.suffix in ['.gz','.png','.webp'] else zipfile.ZIP_DEFLATED)
   with f.open('rb') as h:sha=hashlib.file_digest(h,'sha256').hexdigest()
   records.append({'path':rel,'bytes':f.stat().st_size,'sha256':sha})
  if name==names[0]:z.writestr(root+'/README.txt',readme)
  z.writestr(root+'/checksums-'+name+'.json',json.dumps(records,indent=2))
 with zipfile.ZipFile(target) as z:assert z.testzip() is None
 assert target.stat().st_size<2*1024**3
 with target.open('rb') as h:sha=hashlib.file_digest(h,'sha256').hexdigest()
 assets.append({'name':name,'bytes':target.stat().st_size,'sha256':sha});print(assets[-1],flush=True)
(a.destination/'downloads.json').write_text(json.dumps({'folder':root,'assets':assets},indent=2))
base='https://github.com/acse-yl222/physics-grounded-4d-world-model-framework/releases/download/imperial-corridor-native-20261102/'
script='''"""Download, verify and extract all four Imperial Corridor offline packages."""
from pathlib import Path
import hashlib, json, urllib.request, shutil, zipfile, time
BASE = BASE_VALUE
ASSETS = ASSETS_VALUE
folder = Path.cwd() / 'imperial-corridor-downloads'
folder.mkdir(exist_ok=True)
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
for asset in ASSETS:
 target=folder/asset['name']
 if not target.exists() or sha(target)!=asset['sha256']:
  print('Downloading',asset['name'],f"({asset['bytes']/1e9:.2f} GB)",flush=True)
  for attempt in range(3):
   try:
    with urllib.request.urlopen(BASE+asset['name'],timeout=120) as response, target.with_suffix('.partial').open('wb') as f:shutil.copyfileobj(response,f,8*1024*1024)
    if sha(target.with_suffix('.partial'))!=asset['sha256']:raise ValueError('Checksum mismatch')
    target.with_suffix('.partial').replace(target)
    break
   except Exception:
    if attempt==2:raise
    time.sleep(3)
 print('Extracting',asset['name'],flush=True)
 with zipfile.ZipFile(target) as z:
  for member in z.infolist():
   if not (folder/member.filename).resolve().is_relative_to(folder.resolve()):raise ValueError('Invalid ZIP path')
  z.extractall(folder)
print('Ready:',folder/'imperial-corridor-native')
print('Run start_windows.bat, or run python3 serve.py from that folder.')
'''.replace('BASE_VALUE',repr(base)).replace('ASSETS_VALUE',repr(assets))
(a.destination/'download_all.py').write_text(script)
(a.destination/'SHA256SUMS.txt').write_text(''.join(x['sha256']+'  '+x['name']+'\n' for x in assets))
