import json
import re
import threading
from sqlalchemy import select, delete, update, text
from .models import Material, Entry, Chunk
from .chunking import split_text, options
from .providers import DependencyError

EMPTY = '资料中未找到相关内容'

def rrf(keyword, vector):
    scores = {}
    for route in (keyword, vector):
        for rank, (chunk_id, _) in enumerate(route, 1):
            scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (60 + rank)
    return sorted(scores.items(), key=lambda x: (-x[1], x[0]))

class Retrieval:
    def __init__(self, sessions, engine, embedder, vectors):
        self.sessions, self.engine = sessions, engine
        self.embedder, self.vectors = embedder, vectors
        self.lock = threading.RLock()

    def index(self, material_id, class_id, raw=None):
        opt = options(raw)  # Validate before modifying an existing index.
        with self.lock:
            with self.sessions.begin() as s:
                material = s.scalar(select(Material).where(Material.id == material_id, Material.class_id == class_id))
                if material is None:
                    raise LookupError('资源不存在')
                entry = s.scalar(select(Entry).where(Entry.material_id == material_id, Entry.class_id == class_id))
                processed, pieces, opt = split_text(entry.body_text, opt)
                if not pieces:
                    raise ValueError('预处理后没有可索引文本')
                material.index_status = 'pending'; material.index_error = ''
                s.execute(update(Chunk).where(Chunk.material_id == material_id, Chunk.class_id == class_id).values(index_status='pending'))
            try:
                self.vectors.delete(class_id, material_id)
                with self.sessions.begin() as s:
                    s.execute(delete(Chunk).where(Chunk.material_id == material_id, Chunk.class_id == class_id))
                    entry = s.scalar(select(Entry).where(Entry.material_id == material_id, Entry.class_id == class_id))
                    entry.processed_text = processed; entry.chunk_options = json.dumps(opt, ensure_ascii=False)
                    chunks = [Chunk(class_id=class_id, material_id=material_id, knowledge_entry_id=entry.id,
                        chunk_index=i, start_offset=p.start, end_offset=p.end, coordinate_space=p.coordinate_space,
                        chunk_text=p.text, index_status='pending') for i,p in enumerate(pieces,1)]
                    s.add_all(chunks); s.flush()
                vectors = []
                for start in range(0, len(chunks),32):
                    vectors.extend(self.embedder.embed([c.chunk_text for c in chunks[start:start+32]]))
                self.vectors.put(chunks, vectors)
                with self.sessions.begin() as s:
                    s.execute(update(Chunk).where(Chunk.material_id == material_id, Chunk.class_id == class_id).values(index_status='ready'))
                    material = s.get(Material, material_id)
                    material.index_status = 'ready'; material.index_error = ''
                return {'index_status': 'ready', 'chunk_count': len(chunks)}
            except Exception:
                # First hide every row, then attempt cross-store cleanup. Failure of cleanup
                # never turns orphan vectors into visible SQL records.
                with self.sessions.begin() as s:
                    s.execute(update(Chunk).where(Chunk.material_id == material_id, Chunk.class_id == class_id).values(index_status='failed'))
                    m = s.get(Material, material_id)
                    m.index_status = 'failed'; m.index_error = '索引失败，请检查嵌入与向量服务后重建'
                try:
                    self.vectors.delete(class_id, material_id)
                except Exception:
                    pass
                return {'index_status': 'failed', 'message': '材料已保存，索引失败，可由教师重建'}

    def keyword(self, class_id, query):
        with self.sessions() as s:
            if self.engine.dialect.name == 'mysql':
                rows = s.execute(text('''SELECT id, MATCH(chunk_text) AGAINST (:q IN NATURAL LANGUAGE MODE) AS score
                    FROM knowledge_chunks WHERE class_id=:cid AND index_status='ready'
                    AND MATCH(chunk_text) AGAINST (:q IN NATURAL LANGUAGE MODE)>0
                    ORDER BY score DESC, id LIMIT 50'''), {'q': query, 'cid': class_id})
                return [(r.id,float(r.score)) for r in rows]
            # SQLite is a unit-test adapter only. Compose uses MySQL ngram FULLTEXT.
            tokens = re.findall(r'[a-zA-Z0-9]+|[\u4e00-\u9fff]+', query.lower())
            terms = set()
            for token in tokens:
                if re.search(r'[\u4e00-\u9fff]',token) and len(token)>1:
                    terms.update(token[i:i+2] for i in range(len(token)-1))
                else:
                    terms.add(token)
            rows = s.scalars(select(Chunk).where(Chunk.class_id==class_id, Chunk.index_status=='ready'))
            scored = [(c.id,float(sum(c.chunk_text.lower().count(t) for t in terms))) for c in rows]
            return sorted((x for x in scored if x[1]>0), key=lambda x:(-x[1],x[0]))[:50]

    def search(self, class_id, query, mode='hybrid', top_k=6):
        if not isinstance(query, str) or not query.strip() or len(query)>1000:
            raise ValueError('请输入1–1000字的查询')
        if mode not in ('keyword','vector','hybrid'):
            raise ValueError('未知检索模式')
        if type(top_k) is not int or not 1 <= top_k <= 20:
            raise ValueError('top_k必须为1–20整数')
        query=query.strip()
        keyword = self.keyword(class_id,query) if mode!='vector' else []
        vector=[]
        if mode!='keyword':
            try:
                embedding=self.embedder.embed([query], query=True)[0]
                vector=self.vectors.search(class_id,embedding)
            except Exception as e:
                raise DependencyError('向量检索服务不可用；可改用关键字检索') from e
            # Defense in depth before ranking; do not trust point payload or vector store scope.
            with self.sessions() as s:
                allowed=set(s.scalars(select(Chunk.id).where(Chunk.id.in_([c for c,_ in vector]),
                    Chunk.class_id==class_id, Chunk.index_status=='ready')))
            vector=[(c,score) for c,score in vector if c in allowed and score>=0.35]
        ranking=rrf(keyword,vector) if mode=='hybrid' else (keyword if mode=='keyword' else vector)
        kr={c:(score,i) for i,(c,score) in enumerate(keyword,1)}
        vr={c:(score,i) for i,(c,score) in enumerate(vector,1)}
        hits=[]
        with self.sessions() as s:
            for chunk_id,score in ranking[:top_k]:
                row=s.execute(select(Chunk,Material).join(Material,Material.id==Chunk.material_id).where(
                    Chunk.id==chunk_id,Chunk.class_id==class_id,Material.class_id==class_id,
                    Chunk.index_status=='ready',Material.index_status=='ready')).first()
                if not row:
                    continue
                c,m=row
                hits.append({'chunk_id':c.id,'material_id':m.id,'title':m.title,
                    'chunk_index':c.chunk_index,'start_offset':c.start_offset,'end_offset':c.end_offset,
                    'coordinate_space':c.coordinate_space,'excerpt':c.chunk_text,
                    'source_url':f'/sources/{c.id}','material_url':f'/api/materials/{m.id}',
                    'score':score,'keyword_score':kr.get(c.id,(None,None))[0],
                    'keyword_rank':kr.get(c.id,(None,None))[1],
                    'vector_score':vr.get(c.id,(None,None))[0],
                    'vector_rank':vr.get(c.id,(None,None))[1]})
        return {'mode':mode,'hits':hits,'message':'' if hits else EMPTY}
