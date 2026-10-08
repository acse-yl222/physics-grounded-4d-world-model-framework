"""Analyze frozen development/holdout screening and export a self-contained run."""
import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import numpy as np
from .problem import digest, write_json


def score(case, plan):
    return next(p for p in case['plans'] if p['plan'] == list(plan))


def select_policies(development):
    """Selection consumes development scenarios only, never holdout observations."""
    plans = [p['plan'] for p in development[0]['plans']]
    def top(values):
        return sorted(sorted(range(len(values)), key=lambda i: (-values[i], i))[:2])
    benefits = [[score(c, p)['mean_reduction_fraction'] for c in development] for p in plans]
    return {
        'source_mass': top(np.mean([c['source_sector_au_s'] for c in development], axis=0)),
        'local_concentration': top(np.mean([c['local_sector_means'] for c in development], axis=0)),
        'development_mean': plans[max(range(len(plans)), key=lambda i: np.mean(benefits[i]))],
        'development_worst': plans[max(range(len(plans)), key=lambda i: min(benefits[i]))],
    }


def analyze(directory):
    out = Path(directory)
    results = json.loads((out/'results.json').read_text())
    cfg = json.loads((out/'config.json').read_text())
    if json.loads((out/'status.json').read_text())['status'] != 'complete':
        raise ValueError('Full completed batch required')
    rows=[]
    for case in ('idealized', 'south_ken'):
        for height in cfg['height_factors']:
            group = [r for r in results if r['case']==case and r['height_factor']==height and not r['id'].startswith('sensitivity')]
            development = [r for r in group if r['rotation'] in (0,1)]
            holdout = next(r for r in group if r['rotation']==2)
            oracle = max(holdout['plans'], key=lambda p:p['mean_reduction_fraction'])
            policies = select_policies(development)
            policies['holdout_oracle_diagnostic'] = oracle['plan']
            for name,plan in policies.items():
                evaluated = score(holdout, plan)
                rows.append({'case':case,'height_factor':height,'policy':name,'plan':plan,
                             'development_mean_reduction_pct':100*np.mean([score(c,plan)['mean_reduction_fraction'] for c in development]),
                             'holdout_mean_reduction_pct':100*evaluated['mean_reduction_fraction'],
                             'holdout_regret_pp':100*(oracle['mean_reduction_fraction']-evaluated['mean_reduction_fraction']),
                             'emission_reduction_pct':100*evaluated['emission_reduction_fraction']})
    base=next(r for r in results if r['id']=='south_ken_h1_r0_dx8')
    selected=next(r['plan'] for r in rows if r['case']=='south_ken' and r['height_factor']==1 and r['policy']=='development_mean')
    sensitivity=[]
    for r in [base]+[r for r in results if r['id'].startswith('sensitivity')]:
        oracle=max(r['plans'],key=lambda p:p['mean_reduction_fraction'])
        sensitivity.append({'id':r['id'],'baseline_mean':r['baseline_mean'],
                            'baseline_change_pct':100*(r['baseline_mean']/base['baseline_mean']-1),
                            'fixed_plan':selected,'fixed_plan_reduction_pct':100*score(r,selected)['mean_reduction_fraction'],
                            'oracle_plan':oracle['plan'],'oracle_reduction_pct':100*oracle['mean_reduction_fraction']})
    checks=[d for r in results for d in r['transport_checks']+[r['total_source_check']]]
    summary={'scope':'Exploratory deterministic screening; normalized tracer, no LLM comparison or empirical exposure validation.',
             'flow_cases':len(results),'transport_solves':len(checks),'algebraic_plan_scores':sum(len(r['plans']) for r in results),
             'max_mass_balance_relative_error':max(d['mass_balance_relative_error'] for d in checks),
             'max_scalar_relative_residual':max(d['linear_relative_residual'] for d in checks),
             'max_superposition_relative_error':max(r['superposition_relative_error'] for r in results),
             'max_final_divergence_rms':max(r['flow']['records'][-1]['divergence_rms'] for r in results),
             'total_case_wall_seconds':sum(r['wall_seconds'] for r in results),
             'policies':rows,'sensitivities':sensitivity}
    write_json(out/'analysis.json',summary)
    for name,data in [('policies',rows),('sensitivity',sensitivity),('cases',[{k:r[k] for k in ('id','case','height_factor','rotation','cell_m','duration_s','diffusivity_m2_s','baseline_mean','wall_seconds')} for r in results])]:
        with (out/f'{name}.csv').open('w') as f:
            writer=csv.DictWriter(f,fieldnames=list(data[0]));writer.writeheader();writer.writerows(data)
    plot(out,results,summary)
    return summary


def plot(out,results,summary):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,2,figsize=(12,9),layout='constrained')
    for ax,case in zip(axes[0],['idealized','south_ken']):
        matrix=np.array([[next(r['baseline_mean'] for r in results if r['case']==case and r['height_factor']==h and r['rotation']==w and not r['id'].startswith('sensitivity')) for w in [0,1,2]] for h in [.75,1,1.25]])*1e4
        im=ax.imshow(matrix,cmap='viridis',aspect='auto');fig.colorbar(im,ax=ax,label='Normalized tracer (1e-4 a.u./m3)')
        ax.set(xticks=range(3),xticklabels=['West (dev)','South (dev)','East (holdout)'],yticks=range(3),yticklabels=['0.75','1.00','1.25'],ylabel='Height factor',title=case)
        for (i,j),v in np.ndenumerate(matrix):ax.text(j,i,f'{v:.2f}',ha='center',va='center',color='white' if v<matrix.mean() else 'black')
    ax=axes[1,0]
    names=['source_mass','local_concentration','development_mean','development_worst']
    for i,name in enumerate(names):
        rows=[r for r in summary['policies'] if r['case']=='south_ken' and r['policy']==name]
        ax.bar(np.arange(3)+(i-1.5)*.18,[r['holdout_mean_reduction_pct'] for r in rows],width=.18,label=name.replace('_',' '))
    ax.set(xticks=range(3),xticklabels=['0.75','1','1.25'],xlabel='Height factor',ylabel='Holdout mean reduction (%)',title='South Ken: held-out east wind');ax.legend(fontsize=8)
    ax=axes[1,1];s=summary['sensitivities']
    ax.bar(range(len(s)),[r['baseline_change_pct'] for r in s]);ax.axhline(0,color='black',lw=.5)
    ax.set(xticks=range(len(s)),xticklabels=['8 m base','4 m grid','240 s flow','K = 0.5','K = 2'],ylabel='Baseline concentration change (%)',title='Sensitivity: no grid-convergence claim')
    fig.suptitle('Traffic-source / morphology screening — assumed emissions and simplified flow',fontsize=13)
    fig.savefig(out/'experiment_summary.png',dpi=180);fig.savefig(out/'experiment_summary.pdf');plt.close(fig)


def export(directory):
    from common.storage import Storage
    from common.provenance import snapshot_sources
    from common.contract import validate
    out=Path(directory);storage=Storage.load()
    analyze(out)
    target=out/'export';target.mkdir(exist_ok=False)
    for path in out.iterdir():
        if path.name=='export':continue
        if path.is_dir():shutil.copytree(path,target/path.name)
        else:shutil.copy2(path,target/path.name)
    # Keep original simulation snapshot, and separately capture the analysis/export code.
    snapshot_sources(storage.root,target/'analysis_source_snapshot.tar.gz')
    cfg=json.loads((out/'config.json').read_text());env=json.loads((out/'environment.json').read_text())
    data=np.load(out/'cases/south_ken_h1_r0_dx8/fields.npz')
    response=data['responses'][:,1];mask=data['receptor_mask'];yy,xx=np.indices(mask.shape)
    positions=np.stack([64+(xx[mask]+.5)*8,-128+(yy[mask]+.5)*8,np.full(mask.sum(),12)],axis=1)
    summary=json.loads((out/'analysis.json').read_text())
    plan=next(r['plan'] for r in summary['policies'] if r['case']=='south_ken' and r['height_factor']==1 and r['policy']=='development_mean')
    baseline=response.sum(axis=0);benefit=cfg['source_reduction_fraction']*response[plan].sum(axis=0)
    layers=[]
    for name,values in [('baseline_tracer',baseline),('selected_plan_tracer',baseline-benefit),('tracer_reduction',benefit)]:
        asset=f'data/{name}.json';write_json(target/asset,{'positions':positions.tolist(),'values':values[mask].tolist()})
        layers.append({'id':name,'kind':'scalar_field','format':'json','asset':asset,'sampling':'static',
                       'field':{'name':name,'unit':'a.u./m3'},'display':{'widget':'scalar_field','capabilities':['pick','legend']}})
    artifacts=[]
    for i,path in enumerate(sorted(target.rglob('*'))):
        if not path.is_file():continue
        role='source_snapshot' if path.name=='source_snapshot.tar.gz' else f'artifact_{i}'
        artifacts.append({'id':role,'asset':str(path.relative_to(target)),'sha256':digest(path),'media_type':'application/octet-stream'})
    spatial=json.loads((storage.root/'project/south_ken/project.json').read_text())['spatial']
    spatial['bounds_m']={'min':[64,-128,0],'max':[320,128,128]}
    manifest={'schema_version':'1.1.0','scene_id':'south_ken','simulation':'urban_planning','run_id':out.name,
              'status':'complete','created_at':datetime.now(timezone.utc).isoformat(),
              'provenance':{'code_revision':env['code_revision'],'dirty':True,
                            'parameters':{'configuration':cfg,'scope':summary['scope'],'display':'South Ken h=1 west wind, normalized tracer at 8–16 m averaged and displayed at z=12 m; not breathing-height exposure.','selected_sectors':plan,'array_coordinates':'responses and sources are original ENU ZYX; solver_faces/fluid/inlet remain in rotated solver axes, undo case rotation before geographic use.'},
                            'inputs':[{'id':'prepared_inputs','sha256':digest(target/'inputs.npz')}]},
              'spatial':spatial,'time':{'unit':'s','samples':[]},'layers':layers,'artifacts':artifacts}
    write_json(target/'manifest.json',manifest);validate(target/'manifest.json')
    return target


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory');parser.add_argument('--export',action='store_true')
    args=parser.parse_args()
    if args.export:print(export(args.directory))
    else:print(json.dumps(analyze(args.directory),indent=2))
