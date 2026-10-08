"""JSON tool interface with immutable evaluator identities and per-session budgets.

An external agent calls this interface; no scripted policy is labelled an LLM.
Holdout scores are available only after irrevocable submission.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time

from common.storage import identifier
from .problem import Problem, write_json


CATALOG = [
    {'name': 'inspect_task', 'description': 'Read constraints, geometry candidates and physical scope; no held-out observations.',
     'parameters': {'type': 'object', 'properties': {}, 'additionalProperties': False}},
    {'name': 'validate_plan', 'description': 'Check site availability, count/cost budgets and overlap; does not predict winter loss.',
     'parameters': {'type': 'object', 'properties': {'plan': {'type': 'array', 'items': {'type': 'string'}}}, 'required': ['plan'], 'additionalProperties': False}},
    {'name': 'evaluate_plan', 'description': 'Spend one evaluation on development direct-radiation metrics, including invalid/repeated plans.',
     'parameters': {'type': 'object', 'properties': {'plan': {'type': 'array', 'items': {'type': 'string'}}}, 'required': ['plan'], 'additionalProperties': False}},
    {'name': 'inspect_history', 'description': 'Read prior development evaluations and remaining budget.',
     'parameters': {'type': 'object', 'properties': {}, 'additionalProperties': False}},
    {'name': 'submit_plan', 'description': 'Commit an already evaluated feasible plan; close session, then reveal temporal holdout scores.',
     'parameters': {'type': 'object', 'properties': {'plan': {'type': 'array', 'items': {'type': 'string'}}}, 'required': ['plan'], 'additionalProperties': False}},
]


@contextmanager
def locked(path):
    lock = path.with_suffix('.lock')
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        os.close(fd)
        yield
    finally:
        lock.unlink()


def session_path(problem, session):
    identifier(session, run=True)
    return problem.directory / 'sessions' / f'{session}.json'


def start_session(directory, session, phase, actor):
    problem = Problem(directory)
    constraints = problem.constraints(phase)
    path = session_path(problem, session)
    path.parent.mkdir(parents=True, exist_ok=True)
    with locked(path):
        if path.exists():
            raise FileExistsError('Session already exists')
        state = {'session': session, 'phase': phase, 'actor': actor, 'identity': problem.identity,
                 'evaluation_budget': constraints['evaluation_budget'], 'evaluations_used': 0,
                 'closed': False, 'calls': [], 'evaluations': [problem.evaluate([], phase)]}
        write_json(path, state)
    return {'session': session, 'phase': phase, 'evaluation_budget': state['evaluation_budget'],
            'note': 'Empty plan baseline is free for every method; all requested evaluations are charged.'}


def call_tool(directory, session, name, arguments):
    from jsonschema import Draft202012Validator
    problem = Problem(directory)
    path = session_path(problem, session)
    with locked(path):
        state = json.loads(path.read_text())
        if state['identity'] != problem.identity:
            raise ValueError('Task, input or evaluator changed; start a new session')
        if state['closed']:
            raise ValueError('Session closed after submission')
        entry = next((x for x in CATALOG if x['name'] == name), None)
        if entry is None:
            raise ValueError('Unknown tool')
        Draft202012Validator(entry['parameters']).validate(arguments)
        phase = state['phase']
        start = time.perf_counter()
        if name == 'inspect_task':
            result = {key: problem.task[key] for key in ('task_id', 'scene_id', 'objective', 'candidates',
                      'receptor_count', 'interpretation', 'physical_scope', 'split_note')}
            result['constraints'] = problem.constraints(phase)
        elif name == 'validate_plan':
            errors = problem.validate_plan(arguments['plan'], phase)
            result = {'structurally_valid': not errors, 'errors': errors,
                      'note': 'Winter-loss feasibility still needs evaluation.'}
        elif name == 'evaluate_plan':
            if state['evaluations_used'] >= state['evaluation_budget']:
                raise ValueError('Evaluation budget exhausted')
            state['evaluations_used'] += 1
            result = problem.evaluate(arguments['plan'], phase)
            state['evaluations'].append(result)
        elif name == 'inspect_history':
            result = {'evaluations': state['evaluations'],
                      'remaining_budget': state['evaluation_budget'] - state['evaluations_used']}
        else:
            plan = arguments['plan']
            if problem.validate_plan(plan, phase):
                raise ValueError('Submitted plan fails structural constraints')
            match = next((r for r in state['evaluations'] if r['plan'] == sorted(plan) and r['feasible']), None)
            if match is None:
                raise ValueError('Submit a feasible previously evaluated plan')
            result = {'development': match, 'holdout': problem.evaluate(plan, phase, 'holdout'),
                      'note': 'Holdout failure remains a reported failure; submission cannot be revised.'}
            state['closed'] = True
            state['submission'] = result
        state['calls'].append({'index': len(state['calls']), 'utc': datetime.now(timezone.utc).isoformat(),
                               'name': name, 'arguments': arguments, 'result': result,
                               'wall_seconds': time.perf_counter() - start})
        temporary = path.with_suffix('.tmp')
        write_json(temporary, state)
        temporary.replace(path)
    return result
