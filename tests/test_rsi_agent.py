"""Lifecycle evidence: inheritance, evaluation isolation, budgets and real transport contracts."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from urban_planning.rsi.contracts import INITIAL,REVISION,validate,identity
from urban_planning.rsi.provider import FixtureProvider,ResponsesProvider,ClaudeCodeProvider
from urban_planning.rsi.runner import prepare,Engine,Worker,read,verify,promotion
from urban_planning.rsi.evaluator import Evaluator
from common.storage import Storage
from urban_planning.problem import write_json


class ImprovingFixture(FixtureProvider):
    """Synthetic responses used solely to exercise successful parent-child transitions."""
    def complete(self,prompt,schema,max_output_tokens):
        if prompt['operation']=='act' and 'single-site screening' not in prompt['agent']['planner']:
            value={'action':'submit','plan':[],'reason':'Synthetic initial poor policy.'}
            return {'status':'completed','model':self.model,'usage':{'input_tokens':0,'output_tokens':0},'output':[{'content':[{'type':'output_text','text':json.dumps(value)}]}]}
        return super().complete(prompt,schema,max_output_tokens)


class RsiTests(unittest.TestCase):
    def test_white_city_and_cross_scene_isolation(self):
        import shutil
        source=self.storage.run('south_ken','fixture');target=self.storage.run('white_city','fixture')
        shutil.copytree(source,target)
        cfg=read(self.cfg);cfg['scene_id']='white_city';write_json(self.cfg,cfg)
        with patch('urban_planning.rsi.runner.Storage.load',return_value=self.storage):
            with self.assertRaisesRegex(ValueError,'Task scene differs'):prepare(self.cfg)
            task=read(target/'task.json');task['scene_id']='white_city';write_json(target/'task.json',task)
            prepared=prepare(self.cfg)
        self.assertTrue(prepared.is_relative_to(self.storage.cache_root/'white_city'))

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.base=Path(self.tmp.name)
        repo=Path(__file__).resolve().parents[1]
        self.storage=Storage(repo,self.base,self.base/'cache')
        path=self.storage.run('south_ken','fixture');path.mkdir(parents=True)
        phase={'max_panels':1,'max_cost_units':1,'max_winter_loss_fraction':.6,'excluded_ids':[],'evaluation_budget':2}
        write_json(path/'task.json',{'scene_id':'south_ken','candidates':[{'id':'p00','x_m':0.,'y_m':0.,'z_m':2.,'width_m':2.,'depth_m':2.,'cost_units':1}],
                                    'phases':{'initial':phase,'changed':phase},'objective':'maximize summer subject to winter','physical_scope':'synthetic'})
        arrays={'receptors':np.array([[0.,-2.,0.],[5.,-2.,0.]])}
        for season in ('summer','winter'):
            for split in ('development','holdout'):
                pref=f'{season}_{split}_';arrays[pref+'direct_w_m2']=np.ones((1,2))*100
                arrays[pref+'duration_s']=np.array([3600.]);arrays[pref+'altitude_deg']=np.array([45.]);arrays[pref+'azimuth_deg']=np.array([0.])
        np.savez(path/'background.npz',**arrays)
        cfg=read(repo/'project/south_ken/configs/rsi_agent_v01.json');cfg['input_runs']={'solar':'fixture'}
        self.cfg=self.base/'config.json';write_json(self.cfg,cfg)
        with patch('urban_planning.rsi.runner.Storage.load',return_value=self.storage):self.root=prepare(self.cfg)

    def test_true_lineage_inheritance_and_final_isolation(self):
        Engine(self.root,ImprovingFixture()).evolve()
        frozen=read(self.root/'frozen.json');parent=read(self.root/'revisions'/frozen['selected']/'revision.json')
        self.assertEqual(parent['generation'],1)
        entries=[read(p) for p in (self.root/'revisions').glob('*/revision.json')]
        child=next(x for x in entries if x['generation']==2)
        self.assertEqual(child['parent'],parent['id'])
        self.assertIn(parent['revision']['updater'],child['revision']['updater'])
        before=[json.loads(x) for x in (self.root/'events.jsonl').read_text().splitlines()]
        prompts=[x['prompt'] for x in before if x['kind']=='model_request']
        revision_requests=[x for x in prompts if x['operation']=='revise']
        self.assertEqual(revision_requests[1]['instructions'],parent['revision']['updater'])
        self.assertNotIn('holdout',json.dumps(prompts));self.assertNotIn('initial_final',json.dumps(prompts))
        result=Engine(self.root,ImprovingFixture()).final()
        self.assertEqual(result['scores'][0]['holdout']['summer_reduction_fraction'],.5)
        with self.assertRaisesRegex(ValueError,'frozen'):Engine(self.root,ImprovingFixture()).final()
        with self.assertRaisesRegex(ValueError,'prepared'):Engine(self.root,ImprovingFixture()).evolve()

    def test_evaluator_rejects_test_access_and_final_plan_substitution(self):
        ev=Evaluator(self.root,'evolution')
        with self.assertRaisesRegex(ValueError,'mode'):ev.call({'op':'open','task_id':'initial_final','session':'s'})
        ev=Evaluator(self.root,'final');ev.call({'op':'open','task_id':'initial_final','session':'s'})
        ev.call({'op':'submit','session':'s','plan':[]})
        with self.assertRaisesRegex(ValueError,'committed'):ev.score_submitted({'session':'s','plan':['p00']})
        self.assertNotIn('holdout',ev.score_submitted({'session':'s','plan':[]}))
        with self.assertRaisesRegex(ValueError,'one-shot'):ev.score_submitted({'session':'s','plan':[]})

    def test_bad_duplicate_and_diagnostic_calls_cost_budget(self):
        ev=Evaluator(self.root,'evolution');ev.call({'op':'open','task_id':'initial_development','session':'s'})
        for _ in range(2):self.assertFalse(ev.call({'op':'evaluate','session':'s','plan':['bad']})['feasible'])
        with self.assertRaisesRegex(ValueError,'budget'):ev.call({'op':'diagnose','session':'s','plan':[]})

    def test_inputs_and_frozen_agent_tampering(self):
        Engine(self.root,FixtureProvider()).evolve()
        frozen=read(self.root/'frozen.json');p=self.root/'revisions'/frozen['selected']/'revision.json'
        p.write_text(p.read_text()+' ')
        with self.assertRaisesRegex(ValueError,'Frozen'):Engine(self.root,FixtureProvider()).final()
        p=self.root/'inputs/solar/task.json';p.write_text(p.read_text()+' ')
        with self.assertRaisesRegex(ValueError,'inputs'):verify(self.root)

    def test_non_code_revision_and_failed_promotion(self):
        with self.assertRaises(Exception):validate(dict(INITIAL,evaluator='hacked'),REVISION)
        good=[{'task_id':'x','submitted':True,'score':.3}]
        self.assertFalse(promotion(good,good,0)['promoted'])
        self.assertFalse(promotion(good,[{'task_id':'x','submitted':False,'score':1}],0)['promoted'])
        self.assertTrue(promotion(good,[{'task_id':'x','submitted':True,'score':.4}],0)['promoted'])

    def test_model_failure_is_charged_and_never_scripted_fallback(self):
        class Broken(FixtureProvider):
            def complete(self,*args):raise TimeoutError('test')
        engine=Engine(self.root,Broken())
        with self.assertRaises(TimeoutError):engine.evolve()
        state=read(self.root/'state.json');self.assertEqual(state['status'],'failed')
        self.assertEqual(state['ledger']['model_calls'],state['ledger']['unknown_usage_calls'])
        self.assertGreater(state['ledger']['unknown_usage_calls'],0)
        self.assertEqual(state['ledger']['model_calls'],state['ledger']['unknown_cost_calls'])

    def test_transport_parsing_and_refusal(self):
        with self.assertRaises(ValueError):ResponsesProvider.parse({'status':'incomplete'})
        with self.assertRaises(ValueError):ResponsesProvider.parse({'status':'completed','output':[{'content':[{'type':'refusal'}]}]})
        self.assertEqual(ClaudeCodeProvider.parse({'status':'completed','structured_output':{'x':1}}),{'x':1})
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaisesRegex(ValueError,'Configure'):ResponsesProvider('explicit-model')

    def test_worker_process_and_diagnostics(self):
        with Worker(self.root,'evolution') as worker:
            self.assertTrue(worker.call({'op':'open','task_id':'initial_development','session':'s'})['ok'])
            result=worker.call({'op':'diagnose','session':'s','plan':['p00']})
            self.assertEqual(result['result']['diagnostics']['summer']['affected_receptor_fraction'],.5)

    def test_repeated_promotion_uses_task_means_not_arbitrary_pairing(self):
        parent=[{'task_id':'x','submitted':True,'score':v} for v in (.5,.1)]
        child=[{'task_id':'x','submitted':True,'score':v} for v in (.3,.5)]
        result=promotion(parent,child,0)
        self.assertTrue(result['promoted']);self.assertAlmostEqual(result['mean_gain'],.1)
        self.assertEqual(result['repetitions'],2)

    def test_repeated_final_control_has_no_feedback_between_decisions(self):
        cfg=read(self.cfg);cfg.update(validation_repetitions=2,final_repetitions=2,control_revision=INITIAL)
        write_json(self.cfg,cfg)
        with patch('urban_planning.rsi.runner.Storage.load',return_value=self.storage):root=prepare(self.cfg)
        Engine(root,ImprovingFixture()).evolve();report=Engine(root,ImprovingFixture()).final()
        self.assertEqual(len(report['scores']),4)
        self.assertEqual(len(set(x['task_id'] for x in report['scores'])),4)
        self.assertEqual({x['arm'] for x in report['scores']},{'selected','fixed_seed'})
        events=[json.loads(x) for x in (root/'events.jsonl').read_text().splitlines()]
        last=max(i for i,e in enumerate(events) if e['kind']=='model_request')
        first=min(i for i,e in enumerate(events) if e['kind']=='evaluator' and e['request']['op']=='score_submitted')
        self.assertLess(last,first)

    def test_seed_carry_requires_approved_frozen_predecessor(self):
        frozen=Engine(self.root,ImprovingFixture()).evolve()
        cfg=read(self.cfg);cfg['seed_revision']=read(self.root/'revisions'/frozen['selected']/'revision.json')['revision']
        cfg['seed_origin']={'run_directory':str(self.root),'revision_id':frozen['selected']};write_json(self.cfg,cfg)
        with patch('urban_planning.rsi.runner.Storage.load',return_value=self.storage):child=prepare(self.cfg)
        self.assertEqual(read(child/'seed_origin.json')['revision']['revision'],cfg['seed_revision'])
        Engine(self.root,ImprovingFixture()).final()
        with patch('urban_planning.rsi.runner.Storage.load',return_value=self.storage):
            with self.assertRaisesRegex(ValueError,'before any final'):prepare(self.cfg)


if __name__=='__main__':unittest.main()
