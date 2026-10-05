"""Agent-selected, bounded library growth on an isolated district experiment."""
import json
import re
import subprocess
from pathlib import Path
from img2city import config, kit
from img2city.city.quality import _ask, _write


def choose(out):
    out=Path(out)
    candidates=[]
    for path in sorted(out.glob('buildings/*/refine/result.json')):
        result=json.loads(path.read_text())
        if result.get('unmet'):
            candidates.append({'id':int(path.parent.parent.name),'unmet':result['unmet']})
    if not candidates:
        return {'ids':[], 'reason':'No recorded unmet checks'}
    answer,usage=_ask(
        'You are the Img2City component-learning planner. Select ONE coherent gap cluster '
        'from the supplied failed checks, prioritizing recognition of South Kensington station. '
        'Distinguish missing component expressiveness from parameter tuning and missing evidence. '
        'Use at most three building IDs. The component author can add parts and use _set to '
        'replace incorrect host-spec fields. Return JSON {"cluster":lowercase_snake_case, '
        '"ids":[integers],"reason":string}. Select no IDs if no supported geometry gap exists. '
        'Do not invent geometry here; the component author will receive source images and specs.',
        {'candidates':candidates, 'existing_dialect':json.loads(kit.SPEC_DIALECT_JSON.read_text())},
        [],config.LEARNING_MODEL)
    ids=answer.get('ids'); valid={c['id'] for c in candidates}
    if not isinstance(ids,list) or len(ids)>3 or len(set(ids))!=len(ids) or any(i not in valid for i in ids):
        raise ValueError('Invalid component-learning selection')
    if ids and not re.fullmatch(r'[a-z][a-z0-9_]{0,50}',answer.get('cluster','')):
        raise ValueError('Invalid component cluster name')
    _write(out/'component_learning_plan.json',dict(answer,usage=usage,model=config.LEARNING_MODEL))
    return answer


def run(out,stage):
    out=Path(out).resolve()
    # Growth must never write to the shared library or previous experiment areas.
    for path in [kit.PARTS_LEARNED_PY,kit.SPEC_DIALECT_JSON]:
        if not path.resolve().is_relative_to(out):
            raise ValueError('Component learning requires a library copy inside this output directory')
    plan=choose(out)
    if not plan['ids']:
        _write(out/'component_learning_result.json',dict(status='NO_SUPPORTED_GAP',plan=plan));return
    cluster='astra_'+plan['cluster']
    stage('city.generate',out,'--min-area','0','--assemble-only')
    stage('city.render_regress',out,'--snapshot')
    from img2city.building.typology import CARDS_PATH
    tracked=[kit.PARTS_LEARNED_PY,kit.SPEC_DIALECT_JSON,Path(CARDS_PATH)]
    if any(not p.resolve().is_relative_to(out) for p in tracked):
        raise ValueError('Typology cards must also be isolated')
    before={p:p.read_bytes() for p in tracked}
    work=out/'library_grow'/cluster;work.mkdir(parents=True,exist_ok=True)
    for attempt in range(2):
        args=['--cluster',cluster,'--ids',*[str(i) for i in plan['ids']],
              '--model',config.LEARNING_MODEL,'--judge-model',config.JUDGE_MODEL,
              '--regress-out',str(out),'--adopt','--defer-assembly']
        if attempt:args+=['--feedback-file',str(work/'repair_feedback.txt')]
        log=work/f'attempt_{attempt}.log'
        with log.open('w') as stream:
            result=subprocess.run(config.module_cmd('library.grow','--out',str(out),*args),
                cwd=config.PROJECT_ROOT,env=config.subprocess_env(),stdout=stream,stderr=subprocess.STDOUT)
        if result.returncode==0:
            report=json.loads((work/'report.json').read_text())
            if report['verdict']!='ACCEPT':
                for path,body in before.items():path.write_bytes(body)
            _write(out/'component_learning_result.json',dict(status=report['verdict'],report=report));return
        for path,body in before.items():path.write_bytes(body)
        proposal=(work/'raw.txt').read_text() if (work/'raw.txt').exists() else ''
        (work/'repair_feedback.txt').write_text(proposal+'\nValidation failure:\n'+log.read_text()[-8000:])
    _write(out/'component_learning_result.json',{'status':'VALIDATION_FAILED','log':str(log)})
    # Keep the valid pre-learning specs and still export the complete district.
