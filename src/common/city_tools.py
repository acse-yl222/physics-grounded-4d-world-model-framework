"""The same JSON tool space for South Kensington and White City.

python -m common.city_tools catalog
python -m common.city_tools call south_ken field.sample --arguments '{"module":"wind","x":0,"y":0,"time_s":100}'
"""
import argparse
import json
import subprocess
import sys
from .storage import Storage, within, identifier
from .city import SCENES, audit, sample_field

CATALOG = [
    {'name':'city.inspect','arguments':{},'effect':'read','description':'Inspect available city modules and retained results.'},
    {'name':'field.sample','arguments':{'module':'wind|temperature|solar|pollution|flood','x':'metres','y':'metres','time_s':'seconds','date':'optional YYYYMMDD'},'effect':'read','description':'Sample a recorded field with explicit spatial, height and time semantics.'},
    {'name':'pipeline.plan','arguments':{'run_id':'optional existing trial identifier'},'effect':'read','description':'Check the shared geometry, wind, thermal, solar, tracer and flood pipeline.'},
    {'name':'pipeline.run','arguments':{'stage':'geometry|wind|temperature|temperature3d|pollution|solar|flood|plot|verify|visualize','run_id':'optional existing trial identifier'},'effect':'compute','description':'Run a shared scene pipeline stage in cache; resume a trial for dependent stages; needs solver environment.'},
    {'name':'traffic.run','arguments':{'duration':'optional seconds','speed_factor':'optional (0,2]','seed':'optional integer'},'effect':'compute','description':'Rerun SUMO on retained OSM and synthetic fixed-seed demand; report raw metrics.'},
    {'name':'transport.refresh','arguments':{},'effect':'fetch','description':'Retain a dated TfL stop, route, disruption, camera and arrival snapshot.'},
    {'name':'diurnal.run','arguments':{'device':'optional cpu|cuda'},'effect':'compute','description':'Run the shared state-carrying 3-D daylight thermal diagnostic.'},
    {'name':'planning.prepare','arguments':{},'effect':'compute','description':'Prepare a city-local solar siting task for the common budgeted planning/RSI evaluator.'},
    {'name':'planning.start','arguments':{'session':'identifier','phase':'initial|changed','actor':'name'},'effect':'compute','description':'Start a budgeted planning session on the configured city task.'},
    {'name':'planning.call','arguments':{'session':'identifier','tool':'planning tool name','arguments':'object'},'effect':'compute','description':'Use existing planning tools, constraints, diagnostics and budgets.'},
]


def call(storage,scene,name,arguments):
    if scene not in SCENES:raise ValueError('Unsupported city')
    entry=next((x for x in CATALOG if x['name']==name),None)
    if entry is None:raise ValueError('Unknown city tool')
    if not isinstance(arguments,dict) or set(arguments)-entry['arguments'].keys():raise ValueError('Unknown tool arguments')
    if name=='city.inspect':return audit(storage)['scenes'][scene]
    if name=='field.sample':return sample_field(storage,scene,**arguments)
    if name.startswith('pipeline.'):
        import os
        env=dict(os.environ,UWM_ROOT=str(storage.root));env['PYTHONPATH']=str(storage.root/'src')+os.pathsep+env.get('PYTHONPATH','')
        options=['--dry-run'] if name=='pipeline.plan' else ['--stage',arguments['stage']]
        if 'run_id' in arguments:options+=['--run-id',identifier(arguments['run_id'],run=True)]
        if name=='pipeline.run' and arguments['stage'] not in ('geometry','wind','temperature','temperature3d','pollution','solar','flood','plot','verify','visualize'):raise ValueError('Unknown stage')
        result=subprocess.run([sys.executable,'-m','common.pipeline.run_scene',scene,*options],cwd=storage.root,env=env,capture_output=True,text=True)
        return {'success':result.returncode==0,'stdout':result.stdout,'stderr':result.stderr}
    if name=='traffic.run':
        from traffic.sumo_pipeline import run
        path=run(storage,scene,**arguments)
        return {'directory':str(path),'metrics':json.loads((path/'summary.json').read_text())}
    if name=='transport.refresh':
        from traffic.transport import fetch
        return {'directory':str(fetch(storage,scene))}
    if name=='diurnal.run':
        from urban_flow.physics.city_diurnal import run
        return {'directory':str(run(storage,scene,**arguments))}
    if name=='planning.prepare':
        from urban_planning.city_prepare import prepare_scene
        return {'directory':str(prepare_scene(storage,scene))}
    from urban_planning.tools import start_session,call_tool
    task=json.loads((storage.metadata(scene)/'configs/planning_city_task.json').read_text())
    source=within(storage.assets(scene,'input'),task['input_path'])
    session=identifier(arguments['session'],run=True)
    directory=storage.scratch(scene,'urban_planning','city_session_'+session)
    if name=='planning.start':
        import shutil
        directory.mkdir(parents=True,exist_ok=False)
        for filename in ('task.json','background.npz','input_provenance.json','config.json','spatial.json'):
            shutil.copy2(source/filename,directory/filename)
        return start_session(directory,**arguments)
    if not directory.is_dir():raise ValueError('Start this city planning session before calling its tools')
    return call_tool(directory,arguments['session'],arguments['tool'],arguments['arguments'])


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    sub.add_parser('catalog');sub.add_parser('audit')
    q=sub.add_parser('call');q.add_argument('scene',choices=SCENES);q.add_argument('tool',choices=[t['name'] for t in CATALOG]);q.add_argument('--arguments',default='{}')
    a=p.parse_args(argv)
    result=CATALOG if a.action=='catalog' else audit(Storage.load()) if a.action=='audit' else call(Storage.load(),a.scene,a.tool,json.loads(a.arguments))
    print(json.dumps(result,indent=2,allow_nan=False))
    return 0


if __name__=='__main__':main()
