"""Run against the real Compose stack; never uses unit-test provider doubles."""
import json
import os
import time
from pathlib import Path
import requests

root=Path(__file__).resolve().parents[1]
config=dict(line.split('=',1) for line in (root/'.env').read_text().splitlines() if line and not line.startswith('#') and '=' in line)
base=os.getenv('TEST_BASE_URL',f"http://127.0.0.1:{config.get('APP_PORT','8084')}")
records=[]

def check(name,condition,detail=None):
    records.append({'name':name,'passed':bool(condition),'detail':detail})
    print(('PASS ' if condition else 'FAIL ')+name)
    if not condition:
        (root/'docs/e2e-results.json').write_text(json.dumps({'base_url':base,'checks':records},ensure_ascii=False,indent=2))
        raise AssertionError(name)

def login(name):
    s=requests.Session()
    r=s.post(base+'/api/login',json={'username':name,'password':config['DEMO_PASSWORD']},timeout=20)
    check('登录 '+name,r.status_code==200)
    return s

def search(s,query,mode):
    r=s.post(base+'/api/search',json={'query':query,'mode':mode,'class_id':2},timeout=120)
    check(mode+' HTTP 200: '+query,r.status_code==200,{'status':r.status_code})
    return r.json()['hits']

check('公开健康检查',requests.get(base+'/health',timeout=10).status_code==200)
check('未登录检索401',requests.post(base+'/api/search',json={'query':'借阅'},timeout=10).status_code==401)
teacher=login('teacher1');student=login('student1');other=login('student2')
status=teacher.get(base+'/api/status',timeout=30).json()
check('真实Qdrant可用',status['vector_store']=='ready',status)
for mode in ['keyword','vector','hybrid']:
    hits=search(student,'借阅期限' if mode=='keyword' else '借的书可以延长归还时间吗？',mode)
    check(mode+' 返回本班真实命中',bool(hits) and all('B班' not in h['title'] for h in hits),
        [{'title':h['title'],'chunk_id':h['chunk_id'],'score':h['score'],'vector_score':h['vector_score']} for h in hits])
    h=hits[0];r=student.get(base+f"/api/chunks/{h['chunk_id']}",timeout=10)
    source=r.json()['source'];text=source['original_text'] if source['coordinate_space']=='original' else source['processed_text']
    check(mode+' 字符范围与正文一致',text[h['start_offset']:h['end_offset']]==h['excerpt'])
    check(mode+' 来源页面可打开',student.get(base+h['source_url'],timeout=10).status_code==200)
    check(mode+' 跨班来源404',other.get(base+h['source_url'],timeout=10).status_code==404)
for mode in ['keyword','vector','hybrid']:
    hits=search(student,'紫晶猎户座',mode)
    check(mode+' 伪造班级不泄露B班',all('B班' not in h['title'] and '紫晶猎户座' not in h['excerpt'] for h in hits),{'hit_count':len(hits)})
    check(mode+' B班专有词本班无命中',not hits)
# A query outside the corpus must have neither lexical nor vector evidence.
r=student.post(base+'/api/ask',json={'query':'zxqv847291星际粒子湮灭截面'},timeout=120)
check('无据短回答不生成',r.status_code==200 and r.json().get('answer')=='资料中未找到相关内容' and r.json().get('citations')==[] and r.json().get('generated') is False,{'status':r.status_code,'body':r.json()})
content=(root/'examples/课堂讲义.md').read_bytes()
r=student.post(base+'/api/materials',files={'file':('test.md',content)},timeout=20)
check('学生上传403',r.status_code==403)
r=teacher.post(base+'/api/materials',files={'file':('验收-课堂讲义.md',content)},data={'chunk_options':json.dumps({'strategy':'hierarchy'})},timeout=180)
check('教师上传并索引201',r.status_code==201 and r.json().get('index_status')=='ready',r.json())
mid=r.json()['item']['id']
check('本班学生下载',student.get(base+f'/api/materials/{mid}/download',timeout=10).content==content)
check('跨班下载404',other.get(base+f'/api/materials/{mid}/download',timeout=10).status_code==404)
r=teacher.post(base+f'/api/materials/{mid}/reindex',json={'strategy':'custom','max_length':100,'overlap':0.1,'remove_urls':True},timeout=180)
check('教师更换策略重建',r.status_code==200 and r.json()['index_status']=='ready',r.json())
# Gateway-dependent scenario is reported explicitly, never counted as passed when absent.
chat={'configured':status['chat_configured'],'verified':False}
if status['chat_configured']:
    r=student.post(base+'/api/ask',json={'query':'图书可以借多久？'},timeout=120)
    check('真实网关带引用短回答',r.status_code==200 and r.json().get('generated') and bool(r.json().get('citations')),r.json())
    chat['verified']=True
else:
    r=student.post(base+'/api/ask',json={'query':'借阅期限'},timeout=120)
    check('未配置生成网关明确503',r.status_code==503,{'message':r.json().get('message')})
report={'timestamp':time.strftime('%Y-%m-%d %H:%M:%S'),'base_url':base,'providers':'MySQL ngram + Qdrant + real embedding model','checks':records,'chat':chat,'persistence_material_id':mid}
(root/'docs/e2e-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(f'完成 {len(records)} 项；真实生成网关验收: {chat["verified"]}')
