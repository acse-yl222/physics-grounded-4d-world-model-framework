import json
import re
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urban_flow.paper_rotor.scene_transient import execute
from urban_flow.paper_rotor.resume_scene import prepare_resume

class SceneExecutionTests(unittest.TestCase):
    def test_resume_schedule_includes_requested_endpoint(self):
        for start,end in ((6,300),(286,300)):
            with self.subTest(start=start), tempfile.TemporaryDirectory() as directory:
                case=Path(directory)
                (case/'configuration.json').write_text(json.dumps({'processes':1,'target_seconds':start}))
                for name in ('physical_rotor_history.json','log.pimpleFoam'):
                    (case/name).write_text('{}')
                (case/'system').mkdir()
                (case/'system/controlDict').write_text('startFrom latestTime; endTime 6;\nwriteControl adjustableRunTime; writeInterval 20;\nfunctions { writeControl runTime; writeInterval 2; }')
                checkpoint=case/'processor0'/str(start);checkpoint.mkdir(parents=True)
                for name in ('U','p','k','omega','nut','phi'):
                    (checkpoint/name).write_text('field')
                with patch('urban_flow.paper_rotor.resume_scene.analyze',return_value={'numerical_smoke_checks_passed':True}):
                    prepare_resume(case,end)
                control=(case/'system/controlDict').read_text()
                interval=float(re.search(r'adjustableRunTime; writeInterval ([^;]+)',control)[1])
                count=(end-start)/interval
                self.assertAlmostEqual(count,round(count))
                self.assertLessEqual(interval,20)
                self.assertIn('writeControl runTime; writeInterval 2;',control)

    def test_resume_uses_recorded_parallelism_without_redecomposing(self):
        with tempfile.TemporaryDirectory() as directory:
            case=Path(directory)
            (case/'configuration.json').write_text(json.dumps({'processes':16}))
            (case/'status.json').write_text(json.dumps({'state':'transient_resume_prepared'}))
            with patch('urban_flow.paper_rotor.scene_transient.subprocess.run',return_value=SimpleNamespace(returncode=0)) as run:
                execute(case)
            command=run.call_args.args[0]
            self.assertEqual(command[command.index('--cpus')+1],'16')
            self.assertIn('-np 16 pimpleFoam',command[-1])
            self.assertNotIn('decomposePar',command[-1])
            self.assertIn('>> log.pimpleFoam',command[-1])

    def test_running_case_cannot_be_started_again(self):
        with tempfile.TemporaryDirectory() as directory:
            case=Path(directory);(case/'status.json').write_text(json.dumps({'state':'transient_running'}))
            with patch('urban_flow.paper_rotor.scene_transient.subprocess.run') as run:
                with self.assertRaises(ValueError):execute(case)
                run.assert_not_called()
