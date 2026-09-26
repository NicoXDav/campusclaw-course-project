# CampusClaw · 本班可追溯知识库

**价值**：在本班教学材料中找到可核验的知识，降低逐份翻阅资料的成本。  
**场景**：教师上传讲义 → 系统切分并建立向量索引 → 学生检索 → 打开段落出处；配置生成网关后可得到带引用短回答。  
**不做**：跨班检索、超级管理员、PDF/OCR、流式多轮对话、作业流程、MCP（属于后续课程）。

第四次课的主要交付：[变更说明](openspec/changes/add-traceable-vector-retrieval/proposal.md)、[技术设计](openspec/changes/add-traceable-vector-retrieval/design.md)、[验收规约](openspec/changes/add-traceable-vector-retrieval/specs/knowledge-retrieval/spec.md)、[任务状态](openspec/changes/add-traceable-vector-retrieval/tasks.md)。

先读：[第2/3/4课要求总结](docs/课程2-3-4要求总结.md) · [API说明](docs/API.md) · [验收记录](docs/验收记录.md) · [第四课提交说明](docs/第四课提交说明.md)。

## 启动（标准方式）

需要Docker及Compose。首次需下载容器镜像和真实中文嵌入模型，网络速度影响准备时间。

```sh
python3 scripts/setup_env.py
docker compose up --build -d
docker compose logs -f api
```

打开 <http://127.0.0.1:8084>。健康检查 <http://127.0.0.1:8084/health>。`setup_env.py`自动生成随机数据库和演示账号口令，写入被Git忽略的`.env`，已有文件不会被覆盖。

| 账号 | 角色 | 班级 |
|---|---|---|
| teacher1 | 教师 | 软工1班 |
| student1 | 学生 | 软工1班 |
| teacher2 | 教师 | 软工2班 |
| student2 | 学生 | 软工2班 |

四个账号的口令均为本地`.env`中的`DEMO_PASSWORD`，请在编辑器查看；仓库不包含实际口令。种子口令只在首次创建账号时生效。不要提交`.env`、数据库、上传文件或模型缓存。

只有Nginx绑定宿主机8084端口，API/MySQL/Qdrant不映射宿主端口。默认仅本机可访问。数据库、上传、向量、模型缓存使用独立命名卷。

```sh
docker compose down
docker compose up -d
```

上述重建保留材料和索引。**不要加`-v`**，该参数会删除数据卷。

## 演示顺序

1. teacher1登录，用关键字“借阅期限”检索；查看标题、段号和字符范围，点击“核验原文”。
2. 选择向量，搜索“借的书可以延长归还时间吗？”，观察与原词不同的语义命中；再比较混合排序。
3. 教师工具上传`examples/课堂讲义.md`，选择标题切分；查看ready状态。更换策略后点“按当前策略重建”。
4. student1能读本班资料，API上传返回403；student2不能通过材料/切片ID读取1班内容。
5. A班查询B班专有词“紫晶猎户座”，返回结果绝不能包含B班资料；不存在依据时展示无命中。
6. 配置生成网关后点击“根据资料生成短回答”，回答引用可回到原文；无命中不调用生成模型。

## 模型配置

默认`EMBEDDING_PROVIDER=local`，使用FastEmbed `BAAI/bge-small-zh-v1.5`（512维）。是真实中文语义模型，不是随机向量或字符哈希。第一次运行下载权重并缓存，之后可复用缓存。长切片按token窗口嵌入并聚合，避免超长截断丢失尾部。

若网络不能访问模型源，可在有访问条件的环境预热`models`卷，或改用课程嵌入网关。在`.env`设置：

```dotenv
EMBEDDING_PROVIDER=gateway
EMBEDDING_BASE_URL=https://课程提供的地址/v1
EMBEDDING_API_KEY=在本地填写
EMBEDDING_MODEL=课程提供的嵌入模型名
EMBEDDING_DIM=模型实际维度
QDRANT_COLLECTION=campusclaw_chunks_new_model
```

**更换模型需要新的collection并重建全部材料**，即使维度相同也不能混用向量。所有网关请求仅从后端发起，密钥不进入浏览器。

短回答需要另外配置兼容`/chat/completions`的真实生成网关：

```dotenv
CHAT_BASE_URL=https://课程提供的地址/v1
CHAT_API_KEY=在本地填写
CHAT_MODEL=课程提供的聊天模型名
```

运行`docker compose up -d --force-recreate api web`应用环境配置。Base URL不要重复写`/chat/completions`或`/embeddings`。无生成网关时，三种检索和溯源仍可用；有依据的ask会明确返回503，页面标注“待配置网关”。本仓不把摘录或测试桩伪装为生成模型。

## 验证

```sh
# 容器内运行确定性权限/失败路径测试（测试使用隔离SQLite与测试桩）
docker compose exec api python -m pytest -q
# 实际MySQL、Qdrant、中文模型的HTTP端到端测试
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/e2e.py
# OpenSpec结构验证（Node 20.19+）
npm install
npm run spec:validate
```

测试桩只在`tests/`注入；Compose运行真实MySQL ngram全文索引和真实Qdrant。`scripts/e2e.py`从本地`.env`读取演示口令，不打印密钥，生成`docs/e2e-results.json`。结构验证和业务测试是两回事。

## 工程结构

```text
openspec/changes/add-traceable-vector-retrieval/  第四课四件套
openspec/specs/auth-upload/                      第三课行为基线
app/__init__.py                                 鉴权、材料、检索、问答API
app/models.py                                   MySQL模型与ngram全文索引
app/chunking.py                                 三种纯文本切分
app/retrieval.py                                索引状态、班级过滤、RRF
app/providers.py                                真实嵌入、Qdrant、生成网关
app/templates/ + app/static/                    中文界面与来源页
tests/                                         可重复权限与失败路径测试
scripts/e2e.py                                  真实服务验收
deploy/nginx.conf + compose.yaml                容器部署
```

## 边界与取舍

延续个人第三课Flask前端基础，采用MySQL和Qdrant对齐当前教程的数据链路；没有照搬讲师Go实现。旧作业目录和私人上传资料未被迁入本仓。单实例/单worker适合课程演示，索引重建以锁串行化；跨库失败通过状态和回表过滤保证不可见，支持重试，不宣称分布式原子事务。

余弦阈值0.35和RRF k=60来自课件，但相似度不能证明事实相关。引用编号校验保证指向已检索本班材料，不等于自动验证回答一定被材料蕴含；请点击出处核对。实际验收范围、外部配置缺项见验收记录。
