"""Trusted action/revision contracts. Model text never executes as Python or shell."""
import hashlib
import json
from jsonschema import Draft202012Validator


def object_schema(properties):
    return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}


TEXT={'type':'string','minLength':1,'maxLength':12000}
REVISION=object_schema({'planner':TEXT,'updater':TEXT,
                        'memory':{'type':'array','items':{'type':'string','maxLength':2000},'maxItems':12}})
PROPOSAL=object_schema({'revision':REVISION,'rationale':TEXT})
ACTION=object_schema({'action':{'type':'string','enum':['evaluate','diagnose','submit']},
                      'plan':{'type':'array','items':{'type':'string'},'maxItems':64},
                      'reason':{'type':'string','maxLength':2000}})
INITIAL={'planner':'Find a feasible plan with high summer direct-radiation reduction. Respect winter and site constraints. Use evaluations and diagnostics strategically. Submit a previously evaluated feasible plan before the budget expires.',
         'updater':'Inspect the recorded development failures and decisions. Propose a concrete reusable improvement to the planner and, if warranted, to this update procedure. Retain useful inherited behavior. Do not memorize site IDs as universal solutions. Explain the modification and its expected effect. Never change the evaluator, objective, budgets or final-test access.',
         'memory':[]}


def validate(value,schema):
    Draft202012Validator(schema).validate(value)
    return value


def identity(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
