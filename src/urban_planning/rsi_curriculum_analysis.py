"""Post-freeze descriptive analysis; this module is never imported by the model runner."""
import argparse
from collections import Counter,defaultdict
import csv
import json
from pathlib import Path
import shutil
import numpy as np
from .problem import write_json,digest,Problem,best_result


def read(path):return json.loads(Path(path).read_text())


def episode_costs(events):
    current=None;calls={};costs=defaultdict(lambda:{'provider_requests':0,'input_tokens':0,'output_tokens':0,'reported_cost_usd':0.,'evaluations':0})
    for e in events:
        if e['kind']=='evaluator':
            op=e['request']['op']
            if op=='open':current=e['request']['session']
            if op in ('open','evaluate','diagnose') and current is not None:costs[current]['evaluations']+=1
        elif e['kind']=='model_request':
            calls[e['call_id']]=current
            if current is not None:costs[current]['provider_requests']+=1
        elif e['kind']=='model_response':
            target=calls.get(e['call_id'])
            if target is not None:
                raw=e['response'];usage=raw.get('usage') or {}
                for key in ('input_tokens','output_tokens'):costs[target][key]+=usage.get(key) or 0
                costs[target]['reported_cost_usd']+=raw.get('reported_cost_usd') or 0.
        elif e['kind']=='episode':current=None
    return costs


def has_holdout_result(value):
    if isinstance(value,dict):return value.get('split')=='holdout' or any(has_holdout_result(x) for x in value.values())
    if isinstance(value,list):return any(has_holdout_result(x) for x in value)
    return False


def summarize(directory):
    directory=Path(directory);state=read(directory/'status.json');suite=read(directory/'suite.json')
    if state['status'] not in ('complete','completed_with_failures'):raise ValueError('Wait for authoritative batch completion')
    references=read(directory/'references.json')
    # A post-hoc ceiling, never an online comparator or a development selection aid.
    oracle_path=directory/'test_oracles.json'
    if oracle_path.exists():oracles=read(oracle_path)
    else:
        oracles=[]
        for level in (1,2,3):
            entry=next((e for l in state['lineages'] for e in l['runs'] if e['level']==level),None)
            if entry is None:continue
            root=Path(entry.get('retained',entry['directory']));cfg=read(root/'config.json')
            task=next(t for t in cfg['tasks'] if t['role']=='test');problem=Problem(root/'inputs'/task['input'])
            plans=problem.plans(task['phase']);results=[problem.evaluate(p,task['phase'],'holdout') for p in plans]
            oracles.append({'level':level,'identity':problem.identity,'evaluations':len(plans),'best':best_result(results),
                            'scope':'Post-hoc exhaustive test oracle, unavailable to all online methods and excluded from their budgets.'})
        write_json(oracle_path,oracles)
    for ref in references:ref['posthoc_test_oracle']=next((o for o in oracles if o['level']==ref['level']),None)
    rows=[];decisions=[];audits=[];runs=[];failures=[];episode_failures=[]
    for lineage in sorted(state['lineages'],key=lambda x:x['lineage']):
        frozen_times=[];final_times=[]
        for attempt in lineage.get('superseded_attempts',[]):
            root=Path(attempt.get('retained_evidence_directory',attempt['directory']))
            failures.append({'lineage':lineage['lineage'],'level':attempt['level'],'status':attempt['status'],
                             'directory':str(root),'ledger':attempt['ledger']})
        for entry in lineage['runs']:
            root=Path(entry.get('retained',entry['directory']));s=read(root/'state.json')
            if s['status']!='complete':
                failures.append({'lineage':lineage['lineage'],'level':entry['level'],'status':s['status'],'directory':str(root),'ledger':s.get('ledger',{})});continue
            final=read(root/'final.json');events=[json.loads(x) for x in (root/'events.jsonl').read_text().splitlines()]
            episode_failures.extend({'lineage':lineage['lineage'],'level':entry['level'],'session':e['session'],'failure':e.get('failure')} for e in events if e['kind']=='episode' and not e['submitted'])
            costs=episode_costs(events);episodes={e['session']:e for e in events if e['kind']=='episode'}
            frozen_times.extend(e['utc'] for e in events if e['kind']=='frozen');final_times.extend(e['utc'] for e in events if e['kind']=='final_started')
            requests=[e for e in events if e['kind']=='model_request']
            scored=[i for i,e in enumerate(events) if e['kind']=='evaluator' and e['request']['op']=='score_submitted']
            ops=Counter(e['request']['op'] for e in events if e['kind']=='evaluator')
            audit={'lineage':lineage['lineage'],'level':entry['level'],'request_count_matches':len(requests)==s['ledger']['model_calls'],
                   'no_withheld_results_in_prompts':not any(has_holdout_result(e['prompt']) for e in requests),
                   'decisions_before_scoring':not scored or max(i for i,e in enumerate(events) if e['kind']=='model_request')<min(scored),
                   'evaluation_ledger_matches':sum(ops[k] for k in ('open','evaluate','diagnose','score_submitted'))==s['ledger']['evaluations'],
                   'selected_matches_freeze':final['selected']==read(root/'frozen.json')['selected']}
            if not all(audit[k] for k in ('request_count_matches','no_withheld_results_in_prompts','decisions_before_scoring','evaluation_ledger_matches','selected_matches_freeze')):raise ValueError('Audit failed: '+str(audit))
            audits.append(audit)
            for score in final['scores']:
                # The episode event precedes controller-added final arm/repeat tags.
                session=f"final_{score['arm']}_r{score['repeat']}_{score['base_task_id']}"
                ep=episodes[session]
                value=score['holdout'];valid=bool(score['submitted'] and value and value['feasible'])
                rows.append({'lineage':lineage['lineage'],'level':entry['level'],'method':score['arm'],'repeat':score['repeat'],
                             'submitted':score['submitted'],'holdout_feasible':valid,'nonempty_feasible':valid and bool(value['plan']),
                             'plan':value['plan'] if value else None,'raw_summer_pct':100*value['summer_reduction_fraction'] if value else None,
                             'valid_summer_pct':100*value['summer_reduction_fraction'] if valid else 0.,
                             'winter_loss_pct':100*value['winter_reduction_fraction'] if value else None,
                             **costs[ep['session']]})
            for path in sorted((root/'revisions').glob('*/decision.json')):
                d=read(path);parent=d.get('parent_episodes',[]);child=d.get('child_episodes',[])
                before=read(root/'revisions'/d['parent']/'revision.json')['revision']
                after=read(root/'revisions'/d['candidate']/'revision.json')['revision']
                changes={key+'_changed':before[key]!=after[key] for key in ('planner','updater','memory')}
                decisions.append({'lineage':lineage['lineage'],'level':entry['level'],'candidate':d['candidate'],'parent':d['parent'],
                                  'promoted':d['promoted'],'parent_submission_rate':float(np.mean([e['submitted'] for e in parent])) if parent else None,
                                  'child_submission_rate':float(np.mean([e['submitted'] for e in child])) if child else None,'parent_mean_pct':100*np.mean([x['score'] for x in parent]) if parent else None,
                                  'child_mean_pct':100*np.mean([x['score'] for x in child]) if child else None,
                                  'mean_gain_pp':100*d.get('mean_gain',0.),'repetitions':d.get('repetitions',0),'reason':d['reason'],**changes})
            runs.append({'lineage':lineage['lineage'],'level':entry['level'],'run_id':root.name,'directory':str(root),
                         'selected':final['selected'],'seed_hash':read(root/'revisions'/next(p.name for p in (root/'revisions').iterdir() if p.name.startswith('g000_'))/'revision.json')['revision_sha256'],
                         'selected_hash':read(root/'frozen.json')['revision_sha256'],'ledger':s['ledger'],'resolved_models':s.get('resolved_models'),
                         'evolution_ledger':read(root/'frozen.json')['evolution_ledger']})
        if final_times and frozen_times and min(final_times)<max(frozen_times):raise ValueError('Final evaluation preceded full-lineage freeze')
    baseline_rows=[]
    for reference in references:
        for r in reference['runs']:
            valid=r['holdout']['feasible']
            baseline_rows.append({'level':reference['level'],'method':r['method'],'seed':r['seed'],'calls_used':r['calls_used'],
                                  'holdout_feasible':valid,'valid_summer_pct':100*r['holdout']['summer_reduction_fraction'] if valid else 0.,
                                  'plan':r['holdout']['plan'],'wall_seconds':r['wall_seconds']})
    aggregates=[]
    for level in (1,2,3):
        for method in ('selected','fixed_seed','random_search','single_site_ranking','gp_constrained_ei'):
            group=[r for r in rows+baseline_rows if r['level']==level and r['method']==method]
            if not group:continue
            values=[r['valid_summer_pct'] for r in group]
            aggregates.append({'level':level,'method':method,'n':len(group),'mean_valid_summer_pct':float(np.mean(values)),
                               'min_pct':min(values),'max_pct':max(values),'holdout_feasible_rate':float(np.mean([r['holdout_feasible'] for r in group])),
                               'nonempty_feasible_rate':float(np.mean([r['holdout_feasible'] and bool(r['plan']) for r in group]))})
    deployment=[]
    for level in (1,2,3):
        for method in ('selected','fixed_seed'):
            group=[r for r in rows if r['level']==level and r['method']==method]
            if group:deployment.append({'level':level,'method':method,'n':len(group),**{key:float(np.mean([r[key] for r in group])) for key in ('provider_requests','input_tokens','output_tokens','reported_cost_usd','evaluations')}})
    for row in rows+baseline_rows:
        oracle=next(o for o in oracles if o['level']==row['level'])['best']['summer_reduction_fraction']*100
        if row['valid_summer_pct']>oracle+1e-8:raise ValueError('Online score exceeds its exhaustive test oracle')
    totals={k:sum(r['ledger'].get(k,0) for r in runs) for k in ('model_calls','input_tokens','output_tokens','evaluations','reported_cost_usd','model_seconds','unknown_usage_calls','unknown_cost_calls')}
    # Preserve partial/failed ledgers too; never omit their expense from the batch total.
    for f in failures:
        ledger=f['ledger']
        for k in totals:totals[k]+=ledger.get(k,0)
    output={'suite_id':suite['suite_id'],'provider':state['provider'],'completed_runs':len(runs),'failures':failures,'episode_failures':episode_failures,
            'episodes':rows,'deployment':deployment,'decisions':decisions,'baselines':baseline_rows,'aggregates':aggregates,'runs':runs,
            'audits':audits,'totals':totals,'test_oracles':oracles,'scope':suite['scope'],'transport_repairs':state.get('repair'),
            'interpretation':'Descriptive only: two lineages, correlated source intervals, adaptive promotion; no significance or total-cost superiority claim.'}
    write_json(directory/'analysis.json',output)
    for name,data in [('episodes',rows),('decisions',decisions),('baselines',baseline_rows),('aggregates',aggregates),('deployment',deployment)]:
        if data:
            with (directory/(name+'.csv')).open('w') as f:
                w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    plot(directory,output,references)
    report(directory,output,references,suite)
    return output


def plot(directory,data,references):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,3,figsize=(15,9),layout='constrained')
    methods=['selected','fixed_seed','random_search','single_site_ranking','gp_constrained_ei']
    labels=['Selected','Fixed seed','Random','Ranking','GP search']
    for level,ax in zip((1,2,3),axes[0]):
        for i,method in enumerate(methods):
            values=[r['valid_summer_pct'] for r in data['episodes']+data['baselines'] if r['level']==level and r['method']==method]
            if values:
                ax.scatter(np.linspace(i-.12,i+.12,len(values)),values,s=24,alpha=.65)
                ax.plot([i-.22,i+.22],[np.mean(values)]*2,color='black',lw=2)
        ref=next(r for r in references if r['level']==level)['posthoc_test_oracle']['best']
        ax.axhline(100*ref['summer_reduction_fraction'],ls='--',color='gray',label='Post-hoc test oracle (unbudgeted)')
        ax.set(xticks=range(5),xticklabels=labels,title=f'L{level}: same-task comparison',ylabel='Feasible held-out summer reduction (%)')
        ax.tick_params(axis='x',rotation=20);ax.legend(fontsize=7)
    ax=axes[1,0]
    for lineage in (0,1):
        ds=[d for d in data['decisions'] if d['lineage']==lineage]
        ax.plot([d['level'] for d in ds],[d['mean_gain_pp'] for d in ds],'o-',label=f'Lineage {lineage}')
    ax.axhline(0,color='gray',lw=.8);ax.set(xticks=[1,2,3],xlabel='Curriculum level',ylabel='Promotion mean gain (percentage points)',title='Promotion results (two repetitions)');ax.legend()
    ax=axes[1,1]
    for lineage in (0,1):
        rs=sorted([r for r in data['runs'] if r['lineage']==lineage],key=lambda r:r['level'])
        ax.plot([r['level'] for r in rs],np.cumsum([r['ledger']['reported_cost_usd']+sum(f['ledger'].get('reported_cost_usd',0) for f in data['failures'] if f['lineage']==lineage and f['level']==r['level']) for r in rs]),'o-',label=f'Lineage {lineage}')
    ax.set(xticks=[1,2,3],xlabel='Curriculum level',ylabel='Cumulative CLI list-price estimate (USD)',title='Includes failed attempts, evolution and controls');ax.legend()
    ax=axes[1,2]
    ax.bar([r['level'] for r in references],[r['structurally_feasible_count'] for r in references]);ax.set_yscale('log')
    ax.set(xticks=[1,2,3],xlabel='Curriculum level',ylabel='Structurally feasible plans (log)',title='Increasing option/constraint complexity')
    fig.suptitle('Exploratory RSI curriculum — dots are episodes/seeds, not independent cities',fontsize=14)
    fig.savefig(directory/'summary.png',dpi=170);fig.savefig(directory/'summary.pdf');plt.close(fig)


def report(directory,data,references,suite):
    t=data['totals'];lines=['# RSI 难度阶梯与重复测试结果','',
      f"套件：`{suite['suite_id']}`；模型后端：`{data['provider']}`。固定计划见 `docs/framework/rsi-curriculum-experiment-plan.md`。",'',
      f"完成 {data['completed_runs']} 个小实验；保留 {len(data['failures'])} 个失败运行记录。{len(data['decisions'])} 个候选中 {sum(d['promoted'] for d in data['decisions'])} 个通过重复晋升门槛。",'',
      '接口修复：'+str(data.get('transport_repairs') or '无。'),'',
      '## 同级最终任务结果','',
      '下表为满足最终冬季约束的夏季直接辐照削减百分比均值；无效或未提交计零。Agent 计划每方法每级 4 次（两条序列各两次），实际 n 见 aggregates.csv；随机/GP 各 10 seeds，排序仅一次。中途失败而未执行的任务单列，不冒充已完成 episode。样本相关性和样本数不同，不作显著性检验。','',
      '| 等级 | 冻结 Agent | 固定初始 Agent | 随机搜索 | 单点排序 | GP 搜索 |',
      '| --- | ---: | ---: | ---: | ---: | ---: |']
    for level in (1,2,3):
        vals=[]
        for method in ('selected','fixed_seed','random_search','single_site_ranking','gp_constrained_ei'):
            group=next((x for x in data['aggregates'] if x['level']==level and x['method']==method),None)
            vals.append(f"{group['mean_valid_summer_pct']:.4f}%" if group else '未完成')
        lines.append('| '+str(level)+' | '+' | '.join(vals)+' |')
    lines+=['','候选空间与约束、每任务预算随等级变化。因此不能把跨等级原始得分上升解释为 Agent 能力上升；只作同级比较。常规搜索与 Agent 匹配的是部署物理评价预算，模型调用和进化开销并不相等。GP 前 4 次是随机初始化，在本批 4/5/6 次预算下只有 0/1/2 次自适应选择；单点排序预算不足以筛完所有候选并构造组合。这些是低预算探索性对照，不代表充分调优的优化器。','',
            '## 每轮晋升','', '| 序列 | 等级 | 父代均值 | 候选均值 | 差值（百分点） | 晋升 |','| --- | --- | ---: | ---: | ---: | --- |']
    for d in data['decisions']:
        lines.append(f"| {d['lineage']} | {d['level']} | {d['parent_mean_pct'] or 0:.4f}% | {d['child_mean_pct'] or 0:.4f}% | {d['mean_gain_pp']:+.4f} | {'是' if d['promoted'] else '否'} |")
    lines+=['',f"实际候选中 {sum(d['planner_changed'] for d in data['decisions'])} 个修改 planner，{sum(d['updater_changed'] for d in data['decisions'])} 个修改 updater，{sum(d['memory_changed'] for d in data['decisions'])} 个修改 memory。修改被提出不等于被采纳或具有因果收益。",'',
            '每个父/子版本各两次验证，先后顺序交替。晋升检查有效提交、每任务平均不退步和严格平均增益；不是统计显著性判据。下一等级继承前一级获准版本，跨运行来源保存在 seed_origin.json。','',
            '## 任务难度与边界','', '| 等级 | 结构可行方案数 | 开发物理可行非空方案数 |','| --- | ---: | ---: |']
    for r in references:lines.append(f"| {r['level']} | {r['structurally_feasible_count']} | {r['nonempty_feasible_count']} |")
    lines+=['','另外在模型决策全部完成后，对最终任务进行预算外全枚举（test_oracles.json），作为可达上限而非在线基线。图中的虚线是这个事后测试最优值；references.json 的原始参考仍是按开发数据选择的方案，两者不混用。']
    lines+=['','L1 为单点选择；L2 增加组合、不等成本和禁用站点；L3 增加嵌套尺寸、三项组合、更紧冬季约束。阴影并集仍由相同物理求解器计算。成本/禁用为合成规划条件，源辐照与几何沿用已有数据。','',
            '本批改变的是 planner/updater 指令和记忆；未改变基础模型权重或物理工具。未执行 fixed-updater 消融，所以即便冻结版本改善，也不能把收益因果归于 updater 自身的递归修改。不能据此声称跨天气/跨城市泛化、真实热舒适收益或普遍 RSI 优势。最终任务是新构建的选项/约束组合，但太阳时间留出与已有实验相关且已被研究者检查过。固定初始 Agent 有重复调用波动；若冻结版本仍等于初始版本，两组差异只能视为采样波动。','',
            '## 使用量与审计','',
            f"总后端调用 {t['model_calls']} 次；输入 {t['input_tokens']:,}、输出 {t['output_tokens']:,} tokens；计费评价请求 {t['evaluations']} 次。CLI 标价估计 ${t['reported_cost_usd']:.4f}，不是实际订阅账单。模型等待累计 {t['model_seconds']:.1f} 秒，两条序列并发，此数不等于批次墙钟时间。",'',
            f"完成运行内部另有 {len(data['episode_failures'])} 个未有效提交的 episode；未知 token 用量调用 {t['unknown_usage_calls']} 次，未知费用调用 {t['unknown_cost_calls']} 次（均按后端实际返回情况记录）。",'',
            '使用量包含失败尝试、候选生成、被拒绝修改、验证、最终测试和固定 Agent 对照。常规基线/预算外枚举的 CPU 时间与调用数另列 references.json，不混称为同成本。', '',
            '事件审计核对模型调用和评价记账、请求中未含留出评分、先冻结整条三级进化再进行最终评分、评分前完成全部模型决策、最终选择与冻结文件一致。统计与图表脚本只在决策完成后读取参考结果。', '',
            '## 文件','',
            'analysis.json：逐次结果、汇总、运行位置、全部使用量和审计。episodes.csv：24 次最终 Agent/固定对照结果。decisions.csv：晋升结果。baselines.csv：63 次常规对照。references.json：开发枚举参考和所有基线轨迹。summary.png/pdf：描述性图表。', '',
            '完整源码/输入/模型请求响应/候选差异及最终评分保留在各运行的协议包中。失败记录不会因未进入汇总图而删除。']
    lines+=['','## 每次最终部署的平均开销','', '| 等级 | 方法 | 模型请求 | 输入 tokens | 输出 tokens | CLI 标价估计（USD） |','| --- | --- | ---: | ---: | ---: | ---: |']
    for r in data['deployment']:
        lines.append(f"| {r['level']} | {r['method']} | {r['provider_requests']:.2f} | {r['input_tokens']:.0f} | {r['output_tokens']:.0f} | {r['reported_cost_usd']:.4f} |")
    evolution=sum(r['evolution_ledger']['reported_cost_usd'] for r in data['runs'])
    failed=sum(r['ledger'].get('reported_cost_usd',0) for r in data['failures'])
    lines+=['',f'完成运行的开发、修改和晋升验证标价估计合计 ${evolution:.4f}；失败尝试另计 ${failed:.4f}，均已包含在总额中。每次部署表不摊销上述学习开销；deployment.csv 可用于独立核对。']
    if data['failures']:lines+=['','失败运行：',json.dumps(data['failures'],ensure_ascii=False,indent=2)]
    (directory/'report.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory');args=parser.parse_args()
    data=summarize(args.directory);print(json.dumps({'completed_runs':data['completed_runs'],'promotions':sum(d['promoted'] for d in data['decisions']),'totals':data['totals']},indent=2))
