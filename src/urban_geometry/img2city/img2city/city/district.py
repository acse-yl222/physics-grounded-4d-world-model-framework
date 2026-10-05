"""Complete an existing district through Img2City generation, assembly and agent review."""
from pathlib import Path
import argparse
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor,as_completed
from img2city import config,kit
from img2city.city.quality import _ask,_write,votes,contract,digest


def stage(module,out,*args):
    subprocess.run(config.module_cmd(module,'--out',str(out),*args),cwd=config.PROJECT_ROOT,env=config.subprocess_env(),check=True)


def choose_repairs(out,feedback=None,limit=6):
    data=json.loads((out/'buildings.json').read_text());metas=data['buildings'];ids={m['id'] for m in metas}
    response,usage=_ask('You are Img2City district repair planner. Prioritize the station-house and the buildings whose visible structure most affects recognition of the WHOLE district. Return JSON {"ids":[integer IDs],"reason":string}. Select at most the supplied limit, only from buildings with usable reference evidence. Existing station platform/canopy scene features are separate; do not put them inside the station-house footprint. Do not select tiny shells or buildings whose imagery was rejected.',{'limit':limit,'buildings':[{'id':m['id'],'name':m.get('name'),'type':m.get('btype'),'area':m['area_m2'],'usable':not(out/'buildings'/str(m['id'])/'gate.json').exists()} for m in metas],'feedback':feedback},[str(out/'block_sat_bbox.png')],config.SPEC_MODEL)
    selected=response.get('ids')
    if not isinstance(selected,list) or len(selected)>limit or len(set(selected))!=len(selected) or any(i not in ids for i in selected):raise ValueError('Invalid district repair plan')
    if any((out/'buildings'/str(i)/'gate.json').exists() for i in selected):raise ValueError('Repair planner chose an unverified shell')
    _write(out/'district_workplan.json',dict(response,usage=usage))
    return selected


def inspect_region(out,machine):
    from img2city.city.quality import scene_signature
    assembly=json.loads((out/'assembly_manifest.json').read_text())
    if assembly['signature']!=scene_signature(out):raise RuntimeError('Review would use stale assembly')
    images=[out/name for name in ['block_sat_bbox.png','city_agent_aerial.png','city_agent_top.png','city_agent_street.png']]
    if any(assembly['images'].get(p.name)!=digest(p) for p in images[1:]):raise RuntimeError('Scene images changed after assembly')
    gates=[{'id':p.parent.name,**json.loads(p.read_text())} for p in out.glob('buildings/*/gate.json')]
    features=json.loads((out/'district_features.json').read_text())
    verdict=votes(contract(out,config.JUDGE_MODEL),{'scope':'whole district appearance and scene completeness; only prioritized buildings have individual refinement, so do not infer full building-level verification','machine_checks':machine,'unverified_shells':gates,'scene_features':features,'images_in_order':[p.name for p in images]},[str(p) for p in images],config.JUDGE_MODEL)
    verdict['scope']='REGION_REVIEW_NOT_FULL_BUILDING_ACCEPTANCE';return verdict


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);parser.add_argument('--skip-recovery',action='store_true');parser.add_argument('--wait-recovery-count',type=int,default=0);parser.add_argument('--refine-limit',type=int,default=6);parser.add_argument('--refine-iters',type=int,default=3);parser.add_argument('--workers',type=int,default=3)
    parser.add_argument('--learn-components',action='store_true')
    parser.add_argument('--reuse-refinement',action='store_true',help='Use existing agent checks and retained specs as the learning baseline')
    args=parser.parse_args();out=Path(args.out).resolve();state={'status':'RUNNING','started':time.time(),'model':config.SPEC_MODEL}
    def update(**kw):state.update(kw);_write(out/'district_status.json',state);print('[district]',kw,flush=True)
    try:
        if args.wait_recovery_count:
            update(stage='waiting for reference recovery')
            deadline=time.monotonic()+2400
            while True:
                report=out/'recovery_report.json'
                if report.exists() and len(json.loads(report.read_text()))>=args.wait_recovery_count:break
                if time.monotonic()>deadline:raise TimeoutError('Reference recovery did not finish within budget')
                time.sleep(2)
        if not args.skip_recovery:
            update(stage='reference recovery');stage('imagery.recover_target',out,'--workers',str(args.workers))
        from img2city.city.district_features import plan,BUILD
        if not (out/'district_features.json').exists():
            update(stage='district feature planning');plan(out)
        update(stage='building generation');stage('city.generate',out,'--min-area','0','--no-assemble','--workers',str(args.workers),'--model',config.SPEC_MODEL)
        from img2city.city.generate import refine_building,_send,CLEAR
        backup=out/'blender_before_district.blend'
        if not backup.exists():
            _,error=_send('import bpy\nbpy.ops.wm.save_as_mainfile(filepath='+repr(str(backup))+',copy=True,compress=True)\nprint("BACKUP_OK")',timeout=180)
            if error:raise RuntimeError('Could not preserve current Blender scene: '+error)
        update(stage='feature build validation')
        features=json.loads((out/'district_features.json').read_text())
        result,error=_send(CLEAR+'\n'+kit.load_kit_src()+'\nensure_materials()\n'+BUILD%json.dumps(features['features']),timeout=600)
        if error:raise RuntimeError('Agent feature build failed: '+error)
        update(stage='agent repair planning');selected=choose_repairs(out,limit=args.refine_limit)
        update(stage='building refinement',refine_ids=selected);refinement=[]
        def refine(bid):
            bdir=out/'buildings'/str(bid);frozen=bdir/'refine/checklist.json'
            if args.reuse_refinement and (bdir/'refine/result.json').exists():
                retained=json.loads((bdir/'refine/result.json').read_text())
                return retained['best_pass_rate'],0
            checks=json.loads(frozen.read_text()) if frozen.exists() else None
            return refine_building(str(out),bid,args.refine_iters,'sdk',config.SPEC_MODEL,config.JUDGE_MODEL,inspector_k=3,frozen_checks=checks)
        with ThreadPoolExecutor(max_workers=min(3,args.workers)) as pool:
            jobs={pool.submit(refine,bid):bid for bid in selected}
            for job in as_completed(jobs):
                bid=jobs[job]
                try:score,tokens=job.result();refinement.append({'id':bid,'score':score,'tokens':tokens})
                except Exception as exc:refinement.append({'id':bid,'error':str(exc)})
                update(refinement=refinement)
        if args.learn_components:
            update(stage='agent component learning')
            from img2city.library.district_learning import run
            run(out,stage)
        update(stage='appearance measurement');stage('building.facade_colors',out)
        update(stage='whole district assembly');stage('city.generate',out,'--min-area','0','--assemble-only')
        from img2city.city.make_city import export_blend,verify
        update(stage='district export');blend=export_blend(str(out));glb=out/'district.glb'
        result,error=_send('import bpy\nbpy.ops.export_scene.gltf(filepath='+repr(str(glb))+',export_format="GLB",export_animations=True)\nprint("DISTRICT_GLB_OK")',timeout=900)
        if error:raise RuntimeError('GLB export failed: '+error)
        machine=verify(str(out));update(stage='whole district agent review',blend=blend,glb=str(glb))
        review=inspect_region(out,machine);_write(out/'district_review.json',review)
        # A complete exported district is distinct from full visual acceptance.
        update(status='DISTRICT_EXPORTED',finished=time.time(),regional_review_passed=review['passed'],full_visual_acceptance='NOT_ESTABLISHED',machine_ok=machine['ok'])
    except BaseException as exc:
        update(status='FAILED',finished=time.time(),error=str(exc));raise


if __name__=='__main__':main()
