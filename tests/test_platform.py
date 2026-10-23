import io
import json
import pytest
from test_application import app, login


def test_platform_catalog_requires_authentication(app):
    assert app.test_client().get('/api/platform/catalog').status_code == 401
    catalog = login(app).get('/api/platform/catalog').json
    assert len(catalog['apps']) >= 3
    assert catalog['skills'] and catalog['templates']


def test_template_skill_progressive_loading_and_trace_isolation(app):
    c = login(app)
    data = c.get('/api/platform/catalog').json
    skill = data['skills'][0]
    template = c.post('/api/platform/templates', json={'name':'验收模板','content':'先列结论再列依据 {{question}}'}).json
    base = {'app_id':'study','query':'解释规约驱动开发','template_id':template['id'], 'skill_ids':[skill['id']]}
    bound = c.post('/api/platform/chat', json=base)
    assert bound.status_code == 200, bound.json
    trace = bound.json['trace']
    payload = json.dumps(trace['rounds'][0]['request'], ensure_ascii=False)
    assert '先列结论再列依据' in payload
    assert skill['description'] in payload
    assert 'SKILL_BODY_START' not in payload
    active = c.post('/api/platform/chat', json={**base,'active_skill_id':skill['id']}).json
    assert 'SKILL_BODY_START' in json.dumps(active['trace']['rounds'][0]['request'])
    assert login(app,'student1').get('/api/platform/traces/'+trace['id']).status_code == 404


def test_upload_skill_permissions_and_validation(app):
    c = login(app)
    skill = b'---\nname: writing-helper\ndescription: Rewrite paragraphs clearly\n---\n# Steps\nRead, rewrite, verify.'
    r = c.post('/api/platform/skills',data={'file':(io.BytesIO(skill),'SKILL.md')})
    assert r.status_code == 201
    assert any(s['id']==r.json['id'] for s in c.get('/api/platform/catalog').json['skills'])
    assert login(app,'student1').post('/api/platform/skills', data={'file':(io.BytesIO(skill),'SKILL.md')}).status_code == 403
    assert c.post('/api/platform/skills',data={'file':(io.BytesIO(b'bad'),'SKILL.md')}).status_code == 400


def test_chat_history_and_tools_have_real_results(app):
    c = login(app)
    r = c.post('/api/platform/chat',json={'app_id':'tools','query':'计算 12*(3+4)','tools':True})
    assert r.status_code == 200, r.json
    trace = r.json['trace']
    assert len(trace['rounds']) == 2
    assert '84' in trace['answer']
    assert trace['tool_events'][0]['result']['value'] == 84
    cid = trace['conversation_id']
    second = c.post('/api/platform/chat',json={'app_id':'tools','query':'谢谢','conversation_id':cid}).json
    assert any(m.get('content')=='计算 12*(3+4)' for m in second['trace']['rounds'][0]['request']['messages'])
    assert login(app,'teacher2').post('/api/platform/chat',json={'app_id':'tools','query':'hello','conversation_id':cid}).status_code == 404


def test_retrieval_context_uses_only_hits(app):
    c = login(app)
    r = c.post('/api/platform/chat',json={'app_id':'knowledge','query':'借阅期限','knowledge':True,'retrieval_mode':'keyword'})
    assert r.status_code == 200, r.json
    trace = r.json['trace']
    assert 0 < len(trace['evidence']) <= 4
    assert '紫晶猎户座' not in json.dumps(trace['rounds'],ensure_ascii=False)
    assert 'EVIDENCE' in json.dumps(trace['rounds'])


def test_rejects_unbound_skill_and_invalid_tool_expression(app):
    c = login(app)
    assert c.post('/api/platform/chat',json={'app_id':'study','query':'x','active_skill_id':'builtin-review'}).status_code == 400
    assert c.post('/api/platform/chat',json={'app_id':'tools','query':'计算 2**1000','tools':True}).status_code == 400


@pytest.mark.parametrize('extra',[{'template_id':[]},{'conversation_id':{}},{'knowledge':'false'},{'tools':1},{'mcp':[]},{'skill_ids':[{}]}])
def test_malformed_platform_input_is_rejected(app,extra):
    assert login(app).post('/api/platform/chat',json={'app_id':'study','query':'hello',**extra}).status_code==400


def test_student_cannot_create_template(app):
    assert login(app,'student1').post('/api/platform/templates',json={'name':'x','content':'y'}).status_code==403


def test_failed_tool_request_keeps_trace(app):
    c=login(app)
    assert c.post('/api/platform/chat',json={'app_id':'tools','query':'计算 1/0','tools':True}).status_code==400
    items=c.get('/api/platform/traces').json['items']
    assert items
    trace=c.get('/api/platform/traces/'+items[0]['id']).json
    assert trace['status']=='error' and trace['rounds'][0]['request']['tools']
    assert trace['error']


def test_offline_provider_formats_tool_results_for_readers():
    from app.platform_llm import complete
    result={'content':[{'type':'text','text':json.dumps({'course':'个人项目','deadline':'2026-10-28 00:00 Asia/Shanghai','deliverables':['PDF 报告'],'source':'教师要求'},ensure_ascii=False)}],'isError':False}
    payload={'model':'offline','messages':[{'role':'user','content':'截止日期？'},{'role':'tool','tool_call_id':'call1','content':json.dumps(result,ensure_ascii=False)}]}
    content=complete(payload,{'LLM_PROVIDER':'mock'},[])['choices'][0]['message']['content']
    assert '截止时间：2026-10-28' in content and 'PDF 报告' in content and '"content"' not in content


def test_gateway_payload_is_traced_without_authorization(app,monkeypatch):
    app.config.update(LLM_PROVIDER='gateway',CHAT_BASE_URL='https://gateway.example/v1',CHAT_API_KEY='gateway-test-secret',CHAT_MODEL='course-chat')
    sent=[]
    class Response:
        def raise_for_status(self):pass
        def json(self):return {'choices':[{'message':{'role':'assistant','content':'这是网关测试响应'},'finish_reason':'stop'}]}
    def remote(url,**kwargs):
        sent.append((url,kwargs));return Response()
    monkeypatch.setattr('app.platform_llm.requests.post',remote)
    response=login(app).post('/api/platform/chat',json={'app_id':'study','query':'解释认证'})
    assert response.status_code==200
    trace=response.json['trace']
    assert sent[0][0]=='https://gateway.example/v1/chat/completions'
    assert sent[0][1]['headers']['Authorization']=='Bearer gateway-test-secret'
    assert sent[0][1]['json']==trace['rounds'][0]['request']
    assert 'gateway-test-secret' not in json.dumps(trace)
    assert trace['answer']=='这是网关测试响应'


def test_malformed_gateway_message_is_rejected(app,monkeypatch):
    app.config.update(LLM_PROVIDER='gateway',CHAT_BASE_URL='https://gateway.example',CHAT_API_KEY='test',CHAT_MODEL='test')
    class Response:
        def raise_for_status(self):pass
        def json(self):return {'choices':[{'message':None}]}
    monkeypatch.setattr('app.platform_llm.requests.post',lambda *args,**kwargs:Response())
    assert login(app).post('/api/platform/chat',json={'app_id':'study','query':'hello'}).status_code==400
