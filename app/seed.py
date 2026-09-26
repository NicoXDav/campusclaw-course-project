from sqlalchemy import select
from werkzeug.security import generate_password_hash
from .models import ClassRoom,User,Material,Entry

DOCS={1:('A班-知识库与课程实践', '''# A班课程知识库

## 规约驱动开发
先在OpenSpec中写proposal、design、spec和tasks，评审后按任务实现并验收。规约与代码必须在同一个开发仓库维护。

## 校园图书馆借阅
学生凭校园卡借阅图书，借阅期限为三十天。到期前可以办理一次续借，续借期限为十五天。逾期应先归还书籍再办理新的借阅。

## 实验室开放
A班实验室每周三下午两点到五点开放，进入实验室需要向值班教师登记。实验材料保存在本班知识库。

## 作业提交
第四次课提交开发仓库地址，仓库中应包含OpenSpec变更描述和可追溯知识库检索实现。检索结果必须标注材料标题与切片位置。
'''),2:('B班-专属天文观测安排','''# B班内部通知

B班的专属识别词是紫晶猎户座。天文观测定于周六晚上八点在北侧观测台集合。本通知仅限B班成员查阅，不属于A班资料。
''')}

def seed(sessions,uploads,password):
    with sessions.begin() as s:
        for cid in (1,2):
            if s.get(ClassRoom,cid) is None:
                s.add(ClassRoom(id=cid,name=f'软工{cid}班'))
        s.flush()
        for cid in (1,2):
            for role in ('teacher','student'):
                name=f'{role}{cid}'
                if not s.scalar(select(User).where(User.username==name)):
                    s.add(User(username=name,password_hash=generate_password_hash(password,method='scrypt'),role=role,class_id=cid))
        s.flush()
        # Seed once per fresh database; never regenerate deleted material on restart.
        if not s.scalar(select(Material.id).limit(1)):
            for cid,(title,content) in DOCS.items():
                uid=s.scalar(select(User.id).where(User.username==f'teacher{cid}'))
                stored=f'seed-{cid}.md';(uploads/stored).write_text(content,encoding='utf-8')
                m=Material(class_id=cid,title=title,filename=f'{title}.md',stored_name=stored,uploader_id=uid)
                s.add(m);s.flush()
                s.add(Entry(material_id=m.id,class_id=cid,body_text=content))
