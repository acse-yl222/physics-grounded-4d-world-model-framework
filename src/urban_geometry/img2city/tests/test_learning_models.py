import json
import sys

from img2city import config
from img2city.library import grow


def test_learning_proposal_and_judge_have_separate_model_routes(tmp_path, monkeypatch):
    from img2city.agent import llm
    from img2city.city import generate
    bdir = tmp_path / 'buildings' / '1'
    (bdir / 'refine').mkdir(parents=True)
    (tmp_path / 'buildings.json').write_text(json.dumps({'buildings': [
        {'id': 1, 'pts': [[0, 0], [20, 0], [20, 10], [0, 10]], 'height': 10}]}))
    (bdir / 'refine/result.json').write_text(json.dumps({'unmet': [{'cat': 'feature', 'q': 'arch missing'}]}))
    (bdir / 'spec.json').write_text(json.dumps({'padding': 'x' * 500, 'visible_face': '+x'}))
    monkeypatch.setattr(generate, 'spatial_brief', lambda *a: {'principal_viewed_face': '+x'})
    monkeypatch.setattr(generate, 'ref_photo', lambda p: str(bdir / 'photo.png'))
    monkeypatch.setattr(grow, '_exemplars', lambda: ('', 'MAT_SPEC = {\n"stone": 1\n}\n'))
    monkeypatch.setattr(grow, 'gate0_static', lambda *a: ({'new_arch'}, []))
    monkeypatch.setattr(config, 'LEARNING_MODEL', 'astra-author-test')
    monkeypatch.setattr(config, 'JUDGE_MODEL', 'astra-judge-test')

    def propose(system, prompt, images, model, **kwargs):
        assert model == 'astra-author-test'
        assert 'one fenced Python block' in system
        assert '"visible_face": "+x"' in prompt  # not truncated at 400 chars
        assert '"principal_viewed_face": "+x"' in prompt
        assert images == [str(bdir / 'photo.png')]
        return ('```python\ndef new_arch(p, i):\n    return []\n'
                'PARTS_LEARNED = {"new_arch": new_arch}\n'
                'PER_BUILDING = {"1": [{"type": "new_arch"}]}\n```', {}, None)

    def evaluate(out, bid, extra, model, k, gdir):
        assert model == 'astra-judge-test'
        return {'A': (.3, None), 'B': (.6, None)}

    monkeypatch.setattr(llm, 'vision_call', propose)
    monkeypatch.setattr(grow, 'gate3_lift', evaluate)
    monkeypatch.setattr(sys, 'argv', ['grow', '--out', str(tmp_path), '--cluster', 'arch', '--ids', '1', '--skip-build'])
    grow.main()
    report = json.loads((tmp_path / 'library_grow/arch/report.json').read_text())
    assert report['models'] == {'learning': 'astra-author-test', 'judge': 'astra-judge-test'}
    assert report['verdict'] == 'ACCEPT'


def test_component_vision_dispatch_reaches_the_configured_provider(monkeypatch, tmp_path):
    from img2city.agent import llm, openai_backend
    monkeypatch.setattr(config, 'MODEL_LOG_DIR', tmp_path)
    monkeypatch.setattr(config, 'LLM_PROVIDER', 'codex')
    seen = []
    def call(system, prompt, images, model, **kwargs):
        seen.append((kwargs['transport'], model, images))
        return '```python\npass\n```', {}, None
    monkeypatch.setattr(openai_backend, 'vision_call', call)
    llm.vision_call(grow.SYSTEM, 'author a part', ['reference.png'], model='gpt-6-astra')
    assert seen == [('codex', 'gpt-6-astra', ['reference.png'])]


def test_learning_failure_restores_isolated_library(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from img2city.library import district_learning as dl
    from img2city.building import typology
    for name,attr in [('parts.py','PARTS_LEARNED_PY'),('dialect.json','SPEC_DIALECT_JSON')]:
        path=tmp_path/name;path.write_text('original')
        monkeypatch.setattr(dl.kit,attr,path)
    cards=tmp_path/'cards.json';cards.write_text('original')
    monkeypatch.setattr(typology,'CARDS_PATH',str(cards))
    monkeypatch.setattr(dl,'choose',lambda out: {'ids':[1],'cluster':'arches'})
    calls=[]
    def fail(cmd,**kwargs):
        calls.append(cmd)
        dl.kit.PARTS_LEARNED_PY.write_text('rejected component')
        return SimpleNamespace(returncode=1)
    monkeypatch.setattr(dl.subprocess,'run',fail)
    dl.run(tmp_path,lambda *a: None)
    assert len(calls)==2
    assert dl.kit.PARTS_LEARNED_PY.read_text()=='original'
    assert '--feedback-file' in calls[1]
    assert json.loads((tmp_path/'component_learning_result.json').read_text())['status']=='VALIDATION_FAILED'


def test_learning_refuses_shared_library(tmp_path):
    import pytest
    from img2city.library import district_learning as dl
    with pytest.raises(ValueError,match='library copy'):
        dl.run(tmp_path,lambda *a: None)


def test_regression_check_cannot_create_its_own_baseline(tmp_path,monkeypatch):
    import pytest
    from img2city.city import render_regress
    monkeypatch.setattr(render_regress,'fingerprint',lambda: {'new mesh':[8,6]})
    monkeypatch.setattr(sys,'argv',['regress','--out',str(tmp_path),'--check'])
    with pytest.raises(SystemExit,match='baseline is missing'):
        render_regress.main()
    assert not (tmp_path/'regress_baseline.json').exists()
