"""Responses API transport and an explicitly non-LLM integration-test fixture."""
import json
import os
import urllib.request
import urllib.parse
from .contracts import INITIAL


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise RuntimeError('Model endpoint redirect refused')


class ResponsesProvider:
    kind='responses_api'
    def __init__(self,model,base_url='https://api.openai.com/v1',key_env='OPENAI_API_KEY',timeout=60):
        if not model:raise ValueError('Specify a model ID explicitly')
        parsed=urllib.parse.urlsplit(base_url)
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('Use an endpoint without embedded credentials/query/fragment')
        if parsed.scheme!='https' and not (parsed.scheme=='http' and parsed.hostname in ('localhost','127.0.0.1','::1')):
            raise ValueError('Use HTTPS, or loopback HTTP for a local model')
        self.key=os.environ.get(key_env)
        if not self.key:raise ValueError(f'Configure {key_env} locally before using the API provider')
        self.model=model;self.url=base_url.rstrip('/')+'/responses';self.timeout=timeout
        self.opener=urllib.request.build_opener(NoRedirect())

    def complete(self,prompt,schema,max_output_tokens):
        body={'model':self.model,'store':False,'input':[{'role':'user','content':json.dumps(prompt,ensure_ascii=False)}],
              'max_output_tokens':max_output_tokens,
              'text':{'format':{'type':'json_schema','name':'urban_agent_output','strict':True,'schema':schema}}}
        req=urllib.request.Request(self.url,data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+self.key,'Content-Type':'application/json'})
        with self.opener.open(req,timeout=self.timeout) as response:
            raw=json.load(response)
        # Return raw metadata before parsing: incomplete/refused outputs still incur usage.
        return raw

    @staticmethod
    def parse(raw):
        if raw.get('status')!='completed':raise ValueError('Model response was not completed')
        chunks=[]
        for item in raw.get('output',[]):
            for c in item.get('content',[]):
                if c.get('type')=='refusal':raise ValueError('Model refused structured response')
                if c.get('type')=='output_text':chunks.append(c['text'])
        return json.loads(''.join(chunks))


class FixtureProvider:
    """Scripted plumbing check, NEVER an agent performance result."""
    kind='scripted_test_fixture'
    model='not-a-language-model'
    def complete(self,prompt,schema,max_output_tokens):
        if prompt['operation']=='revise':
            parent=prompt['parent']
            value={'revision':{'planner':parent['planner']+' Use feasible single-site screening before combining sites.',
                               'updater':parent['updater']+' Check that inherited changes preserve feasibility.',
                               'memory':(parent['memory']+['Use development feedback, never final-test scores.'])[-12:]},
                   'rationale':'SCRIPTED TEST FIXTURE: exercise revision and inheritance plumbing.'}
        else:
            history=prompt['history'];brief=prompt['task'];limits=prompt['remaining']
            tried={tuple(x['request']['plan']) for x in history if x.get('request') and x['request']['action']=='evaluate'}
            candidates=[c['id'] for c in brief['candidates'] if c['id'] not in brief['constraints']['excluded_ids']]
            untried=[x for x in candidates if (x,) not in tried]
            feasible=[x['result'] for x in history if x['result'].get('feasible') and 'summer_reduction_fraction' in x['result']]
            best=max(feasible,key=lambda x:x['summer_reduction_fraction'])
            if limits['evaluations']>0 and limits['steps']>1 and untried:
                value={'action':'evaluate','plan':[untried[0]],'reason':'Scripted single-site smoke check.'}
            else:value={'action':'submit','plan':best['plan'],'reason':'Submit the best observed feasible fixture plan.'}
        return {'status':'completed','model':self.model,'id':None,'usage':{'input_tokens':0,'output_tokens':0},
                'output':[{'content':[{'type':'output_text','text':json.dumps(value)}]}]}
    parse=staticmethod(ResponsesProvider.parse)


class ClaudeCodeProvider:
    """Logged-in Claude Code as a stateless structured model transport, not a shell agent."""
    kind='claude_code'
    def __init__(self,model=None,timeout=180):
        import shutil
        import subprocess
        self.executable=shutil.which('claude')
        if not self.executable:raise ValueError('Claude Code is not installed')
        self.model=model or 'configured_default';self.timeout=timeout
        self.version=subprocess.run([self.executable,'--version'],capture_output=True,text=True,timeout=15,check=True).stdout.strip()

    def complete(self,prompt,schema,max_output_tokens):
        import signal
        import subprocess
        import tempfile
        args=[self.executable,'--print','--output-format','json','--json-schema',json.dumps(schema),
              '--tools','','--strict-mcp-config','--mcp-config','{"mcpServers":{}}',
              '--safe-mode','--disable-slash-commands','--no-session-persistence',
              '--setting-sources','','--max-turns','3',
              '--system-prompt','You are an urban planning research agent. Return the requested structured JSON. You have no filesystem or command tools. Only use information in the supplied task and feedback.']
        if self.model!='configured_default':args+=['--model',self.model]
        env=dict(os.environ,CLAUDE_CODE_MAX_OUTPUT_TOKENS=str(max_output_tokens),MAX_STRUCTURED_OUTPUT_RETRIES='0')
        with tempfile.TemporaryDirectory(prefix='urban-rsi-model-') as work:
            proc=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,cwd=work,env=env,start_new_session=True)
            try:stdout,stderr=proc.communicate(json.dumps(prompt,ensure_ascii=False),timeout=self.timeout)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid,signal.SIGKILL);proc.communicate();raise TimeoutError('Claude Code request timed out')
        try:raw=json.loads(stdout)
        except ValueError:raise RuntimeError(f'Claude Code returned no JSON result (exit {proc.returncode})') from None
        usage=raw.get('usage') or {}
        input_names=('input_tokens','cache_creation_input_tokens','cache_read_input_tokens')
        normalized={'output_tokens':usage.get('output_tokens')}
        if type(usage.get('input_tokens')) is int:
            normalized['input_tokens']=sum(usage.get(k,0) for k in input_names)
        return {'status':'completed' if proc.returncode==0 and raw.get('subtype')=='success' and not raw.get('is_error') else 'failed',
                'id':raw.get('session_id'),'model':self.model,'usage':normalized,'model_usage':raw.get('modelUsage'),
                'cli_version':self.version,'reported_cost_usd':raw.get('total_cost_usd'),
                'cli_turns':raw.get('num_turns'),
                'structured_output':raw.get('structured_output'),'result':raw.get('result'),'subtype':raw.get('subtype')}

    @staticmethod
    def parse(raw):
        if raw.get('status')!='completed':raise ValueError('Claude Code request failed or reached its turn limit')
        value=raw.get('structured_output')
        if value is None:value=json.loads(raw.get('result') or '')
        return value
