"""Trusted JSON-lines subprocess. No model code or model-selected file paths run here."""
import json
from pathlib import Path
import sys
import time
import numpy as np
from ..problem import Problem, digest
from ..solar import panel_occlusion, reduced_energy
from .contracts import identity


class Evaluator:
    def __init__(self,root,mode):
        self.root=Path(root);self.config=json.loads((self.root/'config.json').read_text())
        self.tasks={x['id']:x for x in self.config['tasks']}
        self.mode=mode;self.sessions={}
        self.expected=json.loads((self.root/'input_identity.json').read_text())
        self.verify()

    def verify(self):
        from .runner import code_identity
        if json.loads((self.root/'code_identity.json').read_text()) != code_identity():
            raise ValueError('Evaluator code changed')
        current={p:digest(self.root/p) for p in self.expected}
        if current!=self.expected:raise ValueError('Frozen evaluator inputs changed')

    def problem(self,task):
        return Problem(self.root/'inputs'/task['input'])

    def call(self,request):
        self.verify()
        op=request['op']
        if op=='open':
            task=self.tasks[request['task_id']]
            if (task['role']=='test') != (self.mode=='final'):raise ValueError('Task not available in this evaluator mode')
            sid=request['session']
            if sid in self.sessions:raise ValueError('Session already exists')
            p=self.problem(task);cap=self.config['episode_evaluations']
            cap=min(cap,p.constraints(task['phase'])['evaluation_budget'])
            baseline=p.evaluate([],task['phase'],'development')
            self.sessions[sid]={'task':task,'problem':p,'left':cap,'closed':False,'evaluated':{():baseline}}
            brief={k:p.task[k] for k in ['objective','candidates','physical_scope'] if k in p.task}
            brief.update(task_id=task['id'],constraints=p.constraints(task['phase']),evaluation_budget=cap)
            brief['diagnostic_contract']={'cost_evaluations':1,'fields':['affected_receptor_fraction','reduction_kwh_m2_quantiles'],
                                          'per_panel_contributions':False,'registers_for_submission':False}
            return {'task':brief,'baseline':baseline}
        s=self.sessions[request['session']]
        if s['closed']:raise ValueError('Session already closed')
        p=s['problem'];phase=s['task']['phase'];plan=request.get('plan',[])
        if not isinstance(plan,list) or any(not isinstance(x,str) for x in plan):raise ValueError('Plan must contain string IDs')
        if op in ('evaluate','diagnose'):
            if s['left']<=0:raise ValueError('Evaluation budget exhausted')
            s['left']-=1  # Invalid and duplicate evaluation/diagnostic calls are charged.
            result=p.evaluate(plan,phase,'development')
            if op=='evaluate':s['evaluated'][tuple(sorted(plan))]=result
            elif 'summer_reduction_fraction' in result:
                result['diagnostics']=self.diagnostics(p,plan)
            return dict(result,remaining_evaluations=s['left'])
        if op=='submit':
            result=s['evaluated'].get(tuple(sorted(plan)))
            if result is None or not result['feasible']:raise ValueError('Submit a previously evaluated feasible plan')
            s['closed']=True
            s['submitted_plan']=list(result['plan'])
            return result  # No holdout release, even on episode closure.
        if op=='final_score':raise ValueError('Use score_submitted after the session is closed')
        raise ValueError('Unsupported evaluator operation')

    def score_submitted(self,request):
        self.verify();s=self.sessions[request['session']]
        if self.mode!='final' or not s['closed']:raise ValueError('Final score requires a closed final session')
        if s.get('scored') or sorted(request['plan'])!=s['submitted_plan']:
            raise ValueError('Final scoring is one-shot and must match the committed plan')
        s['scored']=True
        return s['problem'].evaluate(request['plan'],s['task']['phase'],'holdout')

    @staticmethod
    def diagnostics(p,plan):
        panels=[p.candidates[x] for x in plan];receptors=p.arrays['receptors'];result={}
        for season in ('summer','winter'):
            prefix=season+'_development_'
            shade=panel_occlusion(receptors,panels,p.arrays[prefix+'altitude_deg'],p.arrays[prefix+'azimuth_deg'])
            energy=reduced_energy(p.arrays[prefix+'direct_w_m2'],p.arrays[prefix+'duration_s'],shade)
            result[season]={'reduction_kwh_m2_quantiles':np.quantile(energy,[0,.5,.95,1]).tolist(),
                            'affected_receptor_fraction':float(np.mean(energy>0))}
        return result


def main():
    evaluator=Evaluator(sys.argv[1],sys.argv[2])
    for line in sys.stdin:
        started=time.perf_counter()
        try:
            request=json.loads(line)
            result=evaluator.score_submitted(request) if request.get('op')=='score_submitted' else evaluator.call(request)
            output={'ok':True,'result':result}
        except Exception as exc:output={'ok':False,'error':str(exc)}
        output['wall_seconds']=time.perf_counter()-started
        print(json.dumps(output,allow_nan=False),flush=True)


if __name__=='__main__':main()
