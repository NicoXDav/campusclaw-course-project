import time
from sqlalchemy import create_engine, String, Text, Integer, ForeignKey, Float, Index
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

class Base(DeclarativeBase):
    pass

class ClassRoom(Base):
    __tablename__ = 'classes'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(20))
    class_id: Mapped[int] = mapped_column(ForeignKey('classes.id'), index=True)

class LoginSession(Base):
    __tablename__ = 'sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    expires_at: Mapped[float] = mapped_column(Float)

class Material(Base):
    __tablename__ = 'materials'
    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey('classes.id'), index=True)
    title: Mapped[str] = mapped_column(String(240))
    filename: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(80), unique=True)
    uploader_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    index_status: Mapped[str] = mapped_column(String(20), default='pending')
    index_error: Mapped[str] = mapped_column(String(240), default='')

class Entry(Base):
    __tablename__ = 'knowledge_entries'
    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey('materials.id'), unique=True)
    class_id: Mapped[int] = mapped_column(Integer, index=True)
    body_text: Mapped[str] = mapped_column(Text().with_variant(LONGTEXT(), 'mysql'))
    processed_text: Mapped[str] = mapped_column(Text().with_variant(LONGTEXT(), 'mysql'), default='')
    chunk_options: Mapped[str] = mapped_column(Text, default='{}')

class Chunk(Base):
    __tablename__ = 'knowledge_chunks'
    __table_args__ = ({'sqlite_autoincrement': True},)
    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(Integer, index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey('materials.id'), index=True)
    knowledge_entry_id: Mapped[int] = mapped_column(ForeignKey('knowledge_entries.id'))
    chunk_index: Mapped[int] = mapped_column(Integer)
    start_offset: Mapped[int] = mapped_column(Integer)
    end_offset: Mapped[int] = mapped_column(Integer)
    coordinate_space: Mapped[str] = mapped_column(String(20))
    chunk_text: Mapped[str] = mapped_column(Text)
    index_status: Mapped[str] = mapped_column(String(20), index=True, default='pending')

# Course placeholders: no assignment/agent/skill business endpoints in this iteration.
class Assignment(Base):
    __tablename__ = 'assignments'
    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey('classes.id'))
    title: Mapped[str] = mapped_column(String(240))
class Assistant(Base):
    __tablename__ = 'assistants'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
class Skill(Base):
    __tablename__ = 'skills'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))

class PlatformRecord(Base):
    __tablename__ = 'platform_records'
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    kind: Mapped[str] = mapped_column(String(24), index=True)
    class_id: Mapped[int] = mapped_column(Integer, index=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    payload: Mapped[str] = mapped_column(Text().with_variant(LONGTEXT(), 'mysql'))
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


def database(url):
    engine = create_engine(url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    if engine.dialect.name == 'mysql':
        from sqlalchemy import text
        with engine.begin() as conn:
            found = conn.execute(text("SHOW INDEX FROM knowledge_chunks WHERE Key_name='ft_chunks'")).first()
            if not found:
                conn.execute(text('ALTER TABLE knowledge_chunks ADD FULLTEXT INDEX ft_chunks (chunk_text) WITH PARSER ngram'))
    return engine, sessionmaker(engine, expire_on_commit=False)
