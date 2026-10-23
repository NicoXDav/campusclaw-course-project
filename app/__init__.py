import hashlib
import json
import os
import re
import secrets
import time
import uuid
import threading
from collections import deque
from pathlib import Path
from functools import wraps
from urllib.parse import urlparse
from flask import Flask, request, jsonify, g, redirect, render_template, send_file
from sqlalchemy import select, delete, text
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash
from .models import database, ClassRoom, User, LoginSession, Material, Entry, Chunk
from .providers import Embeddings, VectorStore, Chat, DependencyError
from .retrieval import Retrieval, EMPTY
from .chunking import options, split_text


def create_app(config=None):
    app=Flask(__name__)
    app.wsgi_app=ProxyFix(app.wsgi_app, x_for=1)
    app.config.update(
        DATABASE_URL=os.getenv('DATABASE_URL','sqlite:///data/app.db'),
        UPLOAD_DIR=os.getenv('UPLOAD_DIR','data/uploads'), MODEL_CACHE=os.getenv('MODEL_CACHE','data/models'),
        QDRANT_URL=os.getenv('QDRANT_URL','http://qdrant:6333'),
        QDRANT_COLLECTION=os.getenv('QDRANT_COLLECTION','campusclaw_chunks'),
        EMBEDDING_PROVIDER=os.getenv('EMBEDDING_PROVIDER','local'),
        EMBEDDING_MODEL=os.getenv('EMBEDDING_MODEL','BAAI/bge-small-zh-v1.5'),
        EMBEDDING_DIM=os.getenv('EMBEDDING_DIM','512'),
        EMBEDDING_BASE_URL=os.getenv('EMBEDDING_BASE_URL',''), EMBEDDING_API_KEY=os.getenv('EMBEDDING_API_KEY',''),
        CHAT_BASE_URL=os.getenv('CHAT_BASE_URL',''), CHAT_API_KEY=os.getenv('CHAT_API_KEY',''),
        CHAT_MODEL=os.getenv('CHAT_MODEL',''), DEMO_PASSWORD=os.getenv('DEMO_PASSWORD',''),
        LLM_PROVIDER=os.getenv('LLM_PROVIDER','mock'), MCP_URL=os.getenv('MCP_URL',''),
        MAX_CONTENT_LENGTH=2*1024*1024+65536, LOGIN_LIMIT=30, LOGIN_WINDOW=60, LOGIN_MIN_SECONDS=0.12,
        COOKIE_SECURE=os.getenv('COOKIE_SECURE','false').lower()=='true', SEED=True, BOOTSTRAP_INDEX=True)
    if config:
        app.config.update(config)
    if not app.config['DEMO_PASSWORD']:
        raise RuntimeError('请在环境变量中设置DEMO_PASSWORD（示例账号口令）')
    uploads=Path(app.config['UPLOAD_DIR']);uploads.mkdir(parents=True,exist_ok=True)
    engine,sessions=database(app.config['DATABASE_URL'])
    embedder=app.config.get('EMBEDDER') or Embeddings(app.config)
    vectors=app.config.get('VECTOR_STORE') or VectorStore(app.config)
    chat=app.config.get('CHAT') or Chat(app.config)
    retrieval=Retrieval(sessions,engine,embedder,vectors)
    app.extensions.update(db=sessions,engine=engine,retrieval=retrieval,chat=chat)

    dummy_hash=generate_password_hash(secrets.token_hex(24),method='scrypt')
    login_attempts={}
    login_lock=threading.Lock()

    def authenticated(teacher=False):
        def decorate(fn):
            @wraps(fn)
            def wrapped(*args,**kwargs):
                if g.user is None:
                    return (jsonify(ok=False,message='未登录或会话已过期'),401) if request.path.startswith('/api/') else redirect('/login')
                if teacher and g.user.role!='teacher':
                    return jsonify(ok=False,message='仅教师可执行此操作'),403
                return fn(*args,**kwargs)
            return wrapped
        return decorate

    @app.before_request
    def identify():
        g.user=None
        token=request.cookies.get('campus_session')
        if token:
            with sessions() as s:
                row=s.get(LoginSession, hashlib.sha256(token.encode()).hexdigest())
                if row and row.expires_at>time.time():
                    g.user=s.get(User,row.user_id)
        if request.method in ('POST','PUT','PATCH','DELETE') and request.headers.get('Origin'):
            if urlparse(request.headers['Origin']).netloc != request.host:
                return jsonify(ok=False,message='拒绝跨站请求'),403

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='same-origin'
        response.headers['X-Frame-Options']='DENY'
        if request.path.startswith('/api/') or g.user:
            response.headers['Cache-Control']='no-store'
        return response

    @app.errorhandler(ValueError)
    def bad_value(error):
        return jsonify(ok=False,message=str(error)),400

    @app.errorhandler(DependencyError)
    def unavailable(error):
        return jsonify(ok=False,message=str(error)),503

    @app.errorhandler(404)
    def missing(_):
        return jsonify(ok=False,message='资源不存在'),404

    @app.errorhandler(413)
    def too_big(_):
        return jsonify(ok=False,message='文件超过2 MiB上限'),413

    def body():
        value=request.get_json(silent=True)
        if not isinstance(value,dict):
            raise ValueError('请求体必须为JSON对象')
        return value

    def own(s,material_id):
        from flask import abort
        value=s.scalar(select(Material).where(Material.id==material_id,Material.class_id==g.user.class_id))
        if value is None:
            abort(404)
        return value

    @app.get('/')
    def home():
        return redirect('/platform' if g.user else '/login')

    @app.get('/login')
    def login_page():
        return render_template('login.html') if not g.user else redirect('/platform')

    @app.get('/materials')
    @authenticated()
    def materials_page():
        return render_template('materials.html')

    @app.get('/search')
    @authenticated()
    def search_page():
        return render_template('search.html',user=g.user)

    @app.post('/api/login')
    def login():
        started=time.monotonic()
        value=body(); username=value.get('username'); password=value.get('password')
        if not isinstance(username,str) or not isinstance(password,str) or len(password)>1024:
            raise ValueError('用户名和密码格式无效')
        with login_lock:
            now=time.monotonic()
            expired=[ip for ip,q in login_attempts.items() if not q or q[-1]<now-app.config['LOGIN_WINDOW']]
            for ip in expired: login_attempts.pop(ip,None)
            key=request.remote_addr or 'unknown'
            if key not in login_attempts and len(login_attempts)>=4096:
                limited=True
            else:
                bucket=login_attempts.setdefault(key,deque())
                while bucket and bucket[0]<now-app.config['LOGIN_WINDOW']: bucket.popleft()
                limited=len(bucket)>=app.config['LOGIN_LIMIT']
                if not limited: bucket.append(now)
        with sessions.begin() as s:
            user=s.scalar(select(User).where(User.username==username.strip()))
            valid=check_password_hash(user.password_hash if user else dummy_hash,password)
            if not user or not valid or limited:
                app.logger.info('Login rejected: %s', 'limited' if limited else ('unknown account' if user is None else 'wrong password'))
                time.sleep(max(0,app.config['LOGIN_MIN_SECONDS']-(time.monotonic()-started)))
                return jsonify(ok=False,message='用户名或密码错误'),401
            old=request.cookies.get('campus_session','')
            s.execute(delete(LoginSession).where(LoginSession.token_hash==hashlib.sha256(old.encode()).hexdigest()))
            s.execute(delete(LoginSession).where(LoginSession.expires_at<time.time()))
            token=secrets.token_urlsafe(32)
            s.add(LoginSession(token_hash=hashlib.sha256(token.encode()).hexdigest(),user_id=user.id,expires_at=time.time()+28800))
            response=jsonify(ok=True,user={'id':user.id,'username':user.username,'role':user.role,'class_id':user.class_id})
        response.set_cookie('campus_session',token,max_age=28800,httponly=True,samesite='Lax',secure=app.config['COOKIE_SECURE'])
        return response

    @app.post('/api/logout')
    def logout():
        token=request.cookies.get('campus_session','')
        with sessions.begin() as s:
            s.execute(delete(LoginSession).where(LoginSession.token_hash==hashlib.sha256(token.encode()).hexdigest()))
        response=jsonify(ok=True);response.delete_cookie('campus_session');return response

    @app.get('/api/me')
    @authenticated()
    def me():
        with sessions() as s:
            name=s.get(ClassRoom,g.user.class_id).name
        return jsonify(ok=True,user={'username':g.user.username,'role':g.user.role,'class_id':g.user.class_id,'class_name':name},
            auth={'scheme':'opaque-token','transport':'HttpOnly Cookie','expires_in_seconds':28800})

    @app.get('/api/materials')
    @authenticated()
    def materials():
        with sessions() as s:
            rows=s.execute(select(Material,Entry,User).join(Entry,Entry.material_id==Material.id).join(User,User.id==Material.uploader_id)
                           .where(Material.class_id==g.user.class_id,Entry.class_id==g.user.class_id).order_by(Material.id.desc()))
            items=[{'id':m.id,'title':m.title,'filename':m.filename,'ext':Path(m.filename).suffix[1:],
                    'excerpt':e.body_text[:120],'uploader':u.username,'created_at':time.strftime('%Y-%m-%d %H:%M',time.localtime(m.created_at)),
                    'index_status':m.index_status,'index_error':m.index_error} for m,e,u in rows]
        return jsonify(ok=True,items=items)

    @app.post('/api/materials')
    @authenticated(teacher=True)
    def upload():
        file=request.files.get('file')
        if not file or not file.filename:
            raise ValueError('请选择文件')
        filename=Path(file.filename.replace('\\','/')).name
        if len(filename)>240:
            raise ValueError('文件名过长')
        suffix=Path(filename).suffix.lower()
        if suffix not in ('.txt','.md'):
            return jsonify(ok=False,message='只支持.txt与.md'),415
        data=file.read(2*1024*1024+1)
        if len(data)>2*1024*1024:
            return too_big(None)
        try:
            content=data.decode('utf-8-sig')
        except UnicodeDecodeError:
            return jsonify(ok=False,message='文件须为UTF-8文本'),422
        if not content.strip() or '\x00' in content:
            return jsonify(ok=False,message='内容为空或含二进制字符'),422
        try:
            raw=json.loads(request.form.get('chunk_options','{}'))
        except json.JSONDecodeError:
            raise ValueError('切分参数JSON无效')
        opt=options(raw)
        if not split_text(content,opt)[1]:
            raise ValueError('预处理后没有可索引文本')
        stored=uuid.uuid4().hex+suffix
        temp=uploads/(stored+'.tmp');final=uploads/stored
        try:
            temp.write_bytes(data)
            with sessions.begin() as s:
                m=Material(class_id=g.user.class_id,title=Path(filename).stem,filename=filename,stored_name=stored,uploader_id=g.user.id)
                s.add(m);s.flush();material_id=m.id
                s.add(Entry(material_id=m.id,class_id=g.user.class_id,body_text=content))
                os.replace(temp,final)
        except Exception:
            temp.unlink(missing_ok=True);final.unlink(missing_ok=True)
            app.logger.exception('Upload transaction failed')
            return jsonify(ok=False,message='材料保存失败，请重试'),500
        status=retrieval.index(material_id,g.user.class_id,opt)
        return jsonify(ok=True,message=status.pop('message','上传并索引成功'),item={'id':material_id,'title':Path(filename).stem},**status),201

    @app.get('/api/materials/<int:material_id>')
    @authenticated()
    def detail(material_id):
        with sessions() as s:
            m=own(s,material_id)
            e=s.scalar(select(Entry).where(Entry.material_id==material_id,Entry.class_id==g.user.class_id))
            u=s.get(User,m.uploader_id)
            return jsonify(ok=True,item={'id':m.id,'title':m.title,'filename':m.filename,'ext':Path(m.filename).suffix[1:],
                'content':e.body_text,'uploader':u.username,'created_at':time.strftime('%Y-%m-%d',time.localtime(m.created_at)),
                'index_status':m.index_status,'index_error':m.index_error,'chunk_options':json.loads(e.chunk_options)})

    @app.get('/api/materials/<int:material_id>/download')
    @authenticated()
    def download(material_id):
        from flask import abort
        with sessions() as s:
            m=own(s,material_id)
            path=(uploads/m.stored_name).resolve()
            if not path.exists():
                abort(404)
            return send_file(path,as_attachment=True,download_name=m.filename)

    @app.post('/api/materials/<int:material_id>/reindex')
    @authenticated(teacher=True)
    def reindex(material_id):
        with sessions() as s:
            own(s,material_id)
        status=retrieval.index(material_id,g.user.class_id,body())
        return jsonify(ok=status['index_status']=='ready',**status),200 if status['index_status']=='ready' else 503

    @app.post('/api/search')
    @authenticated()
    def search():
        data=body()
        return jsonify(ok=True,**retrieval.search(g.user.class_id,data.get('query'),data.get('mode','hybrid'),data.get('top_k',6)))

    def source_data(chunk_id):
        from flask import abort
        with sessions() as s:
            row=s.execute(select(Chunk,Material,Entry).join(Material,Chunk.material_id==Material.id).join(Entry,Chunk.knowledge_entry_id==Entry.id)
                .where(Chunk.id==chunk_id,Chunk.class_id==g.user.class_id,Material.class_id==g.user.class_id,Entry.class_id==g.user.class_id)).first()
            if not row:
                abort(404)
            c,m,e=row
            return {'chunk_id':c.id,'title':m.title,'material_id':m.id,'chunk_index':c.chunk_index,'start_offset':c.start_offset,
                'end_offset':c.end_offset,'coordinate_space':c.coordinate_space,'excerpt':c.chunk_text,
                'original_text':e.body_text,'processed_text':e.processed_text,'index_status':c.index_status}

    @app.get('/api/chunks/<int:chunk_id>')
    @authenticated()
    def chunk(chunk_id):
        return jsonify(ok=True,source=source_data(chunk_id))

    @app.get('/sources/<int:chunk_id>')
    @authenticated()
    def source(chunk_id):
        return render_template('source.html',source=source_data(chunk_id))

    @app.post('/api/ask')
    @authenticated()
    def ask():
        data=body();query=data.get('query')
        result=retrieval.search(g.user.class_id,query,'hybrid',4)
        hits=result['hits']
        if not hits:
            return jsonify(ok=True,answer=EMPTY,citations=[],generated=False)
        output=chat.answer(query,hits)
        if not isinstance(output,dict):
            return jsonify(ok=False,message='模型引用格式无效'),502
        answer=output.get('answer');ids=output.get('citations')
        if answer==EMPTY and ids==[]:
            return jsonify(ok=True,answer=EMPTY,citations=[],generated=True)
        if (not isinstance(answer,str) or not answer.strip() or len(answer)>4000 or
            not isinstance(ids,list) or not ids or any(type(i) is not int or not 1<=i<=len(hits) for i in ids)):
            return jsonify(ok=False,message='模型引用格式无效'),502
        markers={int(x) for x in re.findall(r'\[(\d+)\]',answer)}
        if markers != set(ids):
            return jsonify(ok=False,message='模型引用编号与证据不一致'),502
        return jsonify(ok=True,answer=answer,citations=[dict(hits[i-1],citation=i) for i in sorted(set(ids))],
            generated=True,answer_mode=output.get('mode','gateway'))

    @app.get('/health')
    def health():
        try:
            with engine.connect() as c:
                c.execute(text('SELECT 1'))
            return jsonify(status='ok')
        except Exception:
            return jsonify(status='unavailable'),503

    @app.get('/api/status')
    @authenticated()
    def status():
        try:
            vectors.ensure(); vector_status='ready'
        except Exception:
            vector_status='unavailable'
        configured=bool(app.config['CHAT_BASE_URL'] and app.config['CHAT_API_KEY'])
        return jsonify(ok=True,vector_store=vector_status,embedding_model=app.config['EMBEDDING_MODEL'],
            chat_configured=configured,answer_available=True,
            answer_mode='gateway' if configured else 'extractive',
            class_id=g.user.class_id)

    if app.config['SEED']:
        from .seed import seed
        seed(sessions,uploads,app.config['DEMO_PASSWORD'])
    if app.config['BOOTSTRAP_INDEX']:
        with sessions() as s:
            pending=list(s.execute(select(Material.id,Material.class_id).where(Material.index_status=='pending')))
        for material_id,class_id in pending:
            retrieval.index(material_id,class_id)
    from .platform import register_platform
    register_platform(app,authenticated,body)
    return app
