"""Chat-completions gateway and explicit deterministic, offline test provider."""
import json
import re
import requests
from .providers import Chat, DependencyError


def complete(payload,config,evidence):
    provider=config.get('LLM_PROVIDER','mock')
    if provider=='gateway':
        if not all(config.get(k) for k in ('CHAT_BASE_URL','CHAT_API_KEY','CHAT_MODEL')):
            raise DependencyError('请配置聊天模型网关')
        try:
            response=requests.post(config['CHAT_BASE_URL'].rstrip('/')+'/chat/completions',
                json=payload,headers={'Authorization':'Bearer '+config['CHAT_API_KEY']},timeout=60)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException,ValueError) as error:
            raise DependencyError('聊天模型网关调用失败') from error
    if provider!='mock':
        raise ValueError('未知 LLM_PROVIDER')
    messages=payload['messages']
    query=next(m['content'] for m in reversed(messages) if m['role']=='user')
    names={t['function']['name'] for t in payload.get('tools',[])}
    message={'role':'assistant','content':None}
    if messages[-1]['role']=='tool':
        result=json.loads(messages[-1]['content'])
        if 'value' in result:
            content=f"计算结果：{result['expression']} = {result['value']}"
        elif result.get('content'):
            try:
                details=json.loads(result['content'][0]['text'])
                content=f"{details['course']}阶段性验收\n截止时间：{details['deadline']}\n提交内容："+'、'.join(details['deliverables'])+'\n来源：'+details['source']
            except (ValueError,KeyError,TypeError,IndexError):
                content='工具执行结果：'+messages[-1]['content']
        else:
            content='工具执行结果：'+messages[-1]['content']
    elif 'calculator' in names and re.search(r'计算\s*([\d\s.+*/()\-]+)',query):
        expr=re.search(r'计算\s*([\d\s.+*/()\-]+)',query).group(1).strip()
        message['tool_calls']=[{'id':'call_calc','type':'function','function':{'name':'calculator','arguments':json.dumps({'expression':expr})}}]
        content=None
    elif 'mcp__course_deadline' in names and any(t in query for t in ('截止','中期','验收时间')):
        message['tool_calls']=[{'id':'call_mcp','type':'function','function':{'name':'mcp__course_deadline','arguments':'{"course":"个人项目"}'}}]
        content=None
    elif evidence:
        content=Chat.extractive_answer(query,evidence)['answer']
    elif any('EVIDENCE=[]' in m.get('content','') for m in messages):
        content='资料中未找到相关内容'
    elif any('SKILL_BODY_START' in m.get('content','') for m in messages):
        content='技能执行结果\n1. 明确目标：'+query+'\n2. 拆解步骤：列出输入、处理和验收条件。\n3. 核验：逐项检查事实依据、权限边界和失败路径。'
    else:
        content='针对“'+query+'”，建议先明确目标和约束，再拆解实施步骤，最后通过具体案例验证。'
    message['content']=content
    return {'id':'offline-completion','object':'chat.completion','model':payload['model'],
        'choices':[{'index':0,'message':message,'finish_reason':'tool_calls' if message.get('tool_calls') else 'stop'}],
        'usage':{'prompt_tokens':None,'completion_tokens':None},'provider':'mock'}
