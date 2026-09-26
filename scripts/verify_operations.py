"""Integration checks: briefly stop this project's Qdrant, then recreate containers.
Never deletes volumes. Run only in the dedicated course demonstration stack.
"""
from pathlib import Path
import subprocess,json,hashlib,time
import requests
root=Path(__file__).resolve().parents[1]
config=dict(line.split('=',1) for line in (root/'.env').read_text().splitlines() if line and not line.startswith('#') and '=' in line)
base=f"http://127.0.0.1:{config.get('APP_PORT','8084')}"
report=[]
def compose(*args):
    return subprocess.run(['docker','compose',*args],cwd=root,check=True,capture_output=True,text=True)
def check(name,condition,detail=None):
    report.append({'name':name,'passed':bool(condition),'detail':detail})
    print(('PASS ' if condition else 'FAIL ')+name,flush=True)
    assert condition,name
def login():
    s=requests.Session();r=s.post(base+'/api/login',json={'username':'teacher1','password':config['DEMO_PASSWORD']},timeout=15)
    assert r.status_code==200;return s
s=login();mid=json.loads((root/'docs/e2e-results.json').read_text())['persistence_material_id']
before=s.get(base+f'/api/materials/{mid}',timeout=10).json()['item']['content']
hits_before=s.post(base+'/api/search',json={'query':'可追溯检索','mode':'hybrid'},timeout=90).json()['hits']
ids_before=sorted(h['chunk_id'] for h in hits_before)
try:
    compose('stop','qdrant')
    for mode,expected in [('keyword',200),('vector',503),('hybrid',503)]:
        r=s.post(base+'/api/search',json={'query':'借阅期限','mode':mode},timeout=45)
        check('Qdrant停止时 '+mode,r.status_code==expected,{'status':r.status_code,'hit_count':len(r.json().get('hits',[]))})
    check('关键字依赖故障仍有正文',bool(s.post(base+'/api/search',json={'query':'借阅期限','mode':'keyword'},timeout=10).json()['hits']))
finally:
    compose('start','qdrant')
for _ in range(30):
    try:
        r=s.post(base+'/api/search',json={'query':'借阅期限','mode':'vector'},timeout=5)
        if r.status_code==200:break
    except requests.RequestException:pass
    time.sleep(1)
check('Qdrant恢复后向量检索恢复',r.status_code==200 and bool(r.json()['hits']))
compose('down')
compose('up','-d','--no-build')
s=login()
after=s.get(base+f'/api/materials/{mid}',timeout=10).json()['item']['content']
hits_after=s.post(base+'/api/search',json={'query':'可追溯检索','mode':'hybrid'},timeout=90).json()['hits']
check('down/up后账号可登录',True)
check('down/up后正文不变',before==after,{'material_id':mid,'sha256':hashlib.sha256(after.encode()).hexdigest()})
check('down/up后向量与切片主键不变',ids_before==sorted(h['chunk_id'] for h in hits_after),{'chunk_ids':ids_before})
metadata_code='''import os,json
from sqlalchemy import create_engine,text
from qdrant_client import QdrantClient
engine=create_engine(os.environ['DATABASE_URL'])
with engine.connect() as c:
 rows=list(c.execute(text("SELECT id,class_id,material_id,knowledge_entry_id,chunk_index FROM knowledge_chunks WHERE index_status='ready'")))
 indexes=list(c.execute(text("SHOW INDEX FROM knowledge_chunks WHERE Key_name='ft_chunks'")))
client=QdrantClient(url=os.environ['QDRANT_URL']);name=os.environ.get('QDRANT_COLLECTION','campusclaw_chunks')
points=client.retrieve(name,ids=[r.id for r in rows],with_payload=True,with_vectors=False)
expected={r.id:dict(r._mapping) for r in rows}
assert len(points)==len(rows)
for p in points:
 r=expected[p.id]
 assert set(p.payload)=={'class_id','material_id','knowledge_entry_id','chunk_id','chunk_index'}
 assert p.payload['chunk_id']==p.id==r['id']
 assert all(p.payload[k]==r[k] for k in ['class_id','material_id','knowledge_entry_id','chunk_index'])
assert client.count(name,exact=True).count==len(rows)
assert indexes
print(json.dumps({'ready_chunks':len(rows),'vector_points':len(points),'point_id_matches_sql':True,'payload_has_text':False,'fulltext_index':True,'dimension':client.get_collection(name).config.params.vectors.size}))
'''
r=subprocess.run(['docker','compose','exec','-T','api','python','-'],cwd=root,input=metadata_code,capture_output=True,text=True,check=True)
metadata=json.loads(r.stdout)
check('真实MySQL-Qdrant关联与无旧向量残留',True,metadata)
ps=compose('ps').stdout
(root/'docs/operations-results.json').write_text(json.dumps({'checks':report,'compose_ps':ps},ensure_ascii=False,indent=2))
print('运行验证完成，数据卷已保留。')
