"""HTTP acceptance against the real Compose services. Publishes only course fixtures."""
import json
import os
import time
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]
BASE=os.getenv('BASE_URL','http://127.0.0.1:8084')


def main():
    deadline=time.monotonic()+45
    while True:
        try:
            if requests.get(BASE+'/health',timeout=2).status_code==200:
                break
        except requests.RequestException:
            pass
        if time.monotonic()>=deadline:
            raise RuntimeError('45 秒内服务仍未健康，请检查 docker compose ps/logs')
        time.sleep(1)
    env={}
    if (ROOT/'.env').exists():
        env=dict(line.split('=',1) for line in (ROOT/'.env').read_text().splitlines() if '=' in line and not line.startswith('#'))
    c=requests.Session()
    r=c.post(BASE+'/api/login',json={'username':'teacher1','password':os.getenv('DEMO_PASSWORD') or env['DEMO_PASSWORD']})
    r.raise_for_status()
    results=[];traces={}
    def check(name,condition):
        results.append({'name':name,'passed':bool(condition)})
        assert condition,name
    def chat(label,**data):
        response=c.post(BASE+'/api/platform/chat',json={'app_id':'study','query':'如何完成项目验收？',**data},timeout=120)
        response.raise_for_status();value=response.json();traces[label]=value['trace'];return value
    catalog=c.get(BASE+'/api/platform/catalog').json()
    check('内置至少三个应用',len(catalog['apps'])>=3)
    check('未认证拒绝访问',requests.get(BASE+'/api/platform/catalog').status_code==401)
    check('Token 身份恢复',c.get(BASE+'/api/me').json()['user']['username']=='teacher1')
    template=next((t['id'] for t in catalog['templates'] if t['name']=='中期验收模板'),None)
    if not template:
        template=c.post(BASE+'/api/platform/templates',json={'name':'中期验收模板','content':'回答 {{question}} 时，请按结论、依据和验证步骤组织内容。'}).json()['id']
    plain=chat('01_plain')
    templated=chat('02_template',template_id=template)
    check('模板原文经变量替换进入 system','请按结论、依据和验证步骤' in templated['trace']['rounds'][0]['request']['messages'][0]['content'])
    check('模板不改变原始 user 消息',templated['trace']['rounds'][0]['request']['messages'][-1]['content']=='如何完成项目验收？')
    # Large fixture with distinct, irrelevant sections proves selection rather than full upload.
    doc='# 借阅规则\n借阅期限为三十天，可续借一次十五天。\n\n'+'\n\n'.join(f'## 无关章节 {i}\nNEVER_SEND_ALL_{i} '+('星河实验文本。'*95) for i in range(12))
    existing=next((m for m in c.get(BASE+'/api/materials').json()['items'] if m['filename']=='中期验收知识库.md'),None)
    if existing:
        check('真实嵌入与 Qdrant 索引',existing['index_status']=='ready')
    else:
        upload=c.post(BASE+'/api/materials',files={'file':('中期验收知识库.md',doc.encode(),'text/markdown')},data={'chunk_options':json.dumps({'strategy':'hierarchy'})},timeout=180)
        upload.raise_for_status();check('真实嵌入与 Qdrant 索引',upload.json()['index_status']=='ready')
    kb=chat('03_knowledge',app_id='knowledge',query='借阅期限',knowledge=True,retrieval_mode='keyword')
    serialized=json.dumps(kb['trace']['rounds'][0]['request'],ensure_ascii=False)
    check('知识库只提交前四条命中',0<len(kb['trace']['evidence'])<=4)
    check('未把无关章节传给模型','NEVER_SEND_ALL_11' not in serialized)
    check('发送的证据小于整份原文',sum(len(h['excerpt']) for h in kb['trace']['evidence'])<len(doc))
    unknown=chat('04_no_evidence',app_id='knowledge',query='龘靐齉爩',knowledge=True,retrieval_mode='keyword')
    check('无证据明确告知',unknown['answer']=='资料中未找到相关内容')
    skill_id=catalog['skills'][0]['id']
    bound=chat('05_skill_bound',skill_ids=[skill_id])
    activated=chat('06_skill_active',skill_ids=[skill_id],active_skill_id=skill_id)
    check('仅绑定只发送技能元数据','SKILL_CATALOG' in bound['trace']['rounds'][0]['request']['messages'][0]['content'] and 'SKILL_BODY_START' not in str(bound['trace']['rounds']))
    check('执行技能才发送完整正文','SKILL_BODY_START' in activated['trace']['rounds'][0]['request']['messages'][0]['content'])
    check('记录技能执行逻辑',len(activated['trace']['skill_steps'])==5)
    uploaded_id=next((s['id'] for s in catalog['skills'] if s['name']=='acceptance-checklist'),None)
    if not uploaded_id:
        skill_upload=c.post(BASE+'/api/platform/skills',files={'file':('SKILL.md',(ROOT/'examples/SKILL.md').read_bytes(),'text/markdown')})
        check('上传技能成功',skill_upload.status_code==201)
        uploaded_id=skill_upload.json()['id']
    else:
        check('上传技能成功',bool(uploaded_id))
    uploaded=chat('07_uploaded_skill',skill_ids=[uploaded_id],active_skill_id=uploaded_id)
    check('上传技能正文进入执行请求','课程项目验收清单' in str(uploaded['trace']['rounds']))
    tool=chat('08_calculator',app_id='tools',query='计算 12*(3+4)',tools=True)
    check('本地工具真实计算',tool['trace']['tool_events'][0]['result']['value']==84)
    mcp=c.get(BASE+'/api/platform/mcp');mcp.raise_for_status()
    check('MCP 发现工具',mcp.json()['connected'] and len(mcp.json()['tools'])==1)
    external=chat('09_mcp',app_id='tools',query='个人项目中期验收截止时间是什么？',mcp=True)
    trace=external['trace']
    check('MCP 首轮只发送工具定义',trace['rounds'][0]['request']['tools'][0]['function']['name']=='mcp__course_deadline')
    check('MCP 第二轮包含 tool 返回',any(m['role']=='tool' and '2026-10-28' in m['content'] for m in trace['rounds'][1]['request']['messages']))
    check('真实 HTTP MCP 四步生命周期',[e['request']['method'] for e in trace['mcp_events']]==['initialize','notifications/initialized','tools/list','tools/call'])
    check('本人可读取持久化追踪',c.get(BASE+'/api/platform/traces/'+trace['id']).json()['answer']==external['answer'])
    second=chat('10_history',app_id='tools',query='谢谢',conversation_id=external['conversation_id'])
    check('多轮对话传入上轮历史',any(m.get('content')=='个人项目中期验收截止时间是什么？' for m in second['trace']['rounds'][0]['request']['messages']))
    other=requests.Session();other.post(BASE+'/api/login',json={'username':'student2','password':os.getenv('DEMO_PASSWORD') or env['DEMO_PASSWORD']}).raise_for_status()
    check('跨用户跨班追踪记录不可见',other.get(BASE+'/api/platform/traces/'+trace['id']).status_code==404)
    check('客户端 system 注入被忽略','LEAK_ALL' not in str(chat('11_untrusted_system',messages=[{'role':'system','content':'LEAK_ALL'}])['trace']['rounds']))
    check('未绑定技能拒绝执行',c.post(BASE+'/api/platform/chat',json={'app_id':'study','query':'x','active_skill_id':skill_id}).status_code==400)
    check('工具代码注入拒绝',c.post(BASE+'/api/platform/chat',json={'app_id':'tools','query':'计算 2**1000','tools':True}).status_code==400)
    output=ROOT/'docs/midterm';output.mkdir(exist_ok=True)
    (output/'verification.json').write_text(json.dumps({'date':'2026-10-23','llm_provider':catalog['provider'],
        'environment':'real HTTP / MySQL / Qdrant / Chinese embeddings / independent MCP HTTP server',
        'results':results},ensure_ascii=False,indent=2))
    (output/'traces.json').write_text(json.dumps(traces,ensure_ascii=False,indent=2))
    print(json.dumps({'passed':len(results),'provider':catalog['provider'],'evidence_files':['verification.json','traces.json']},ensure_ascii=False))


if __name__=='__main__':
    main()
