# CampusClaw · 个人 AI 应用平台

个人项目阶段性验收（2026-10-23）。孙翌程，2601210437。

开发仓库：<https://github.com/NicoXDav/campusclaw-course-project>

平台面向课程学习与个人项目实践，将应用、提示词模板、本班知识库、Skill 和工具整合在一个工作空间。登录后进入 `/platform`。保留原有认证、材料管理、知识检索和出处页面。

## 中期验收交付

| 要求 | 实现入口 | 证据 |
|---|---|---|
| 多个 AI 应用 | 学习规划助手、课程知识助手、效率工具助手 | `app/platform.py` 的应用目录；平台截图 |
| 提示词模板 | 内置模板、教师自定义模板、变量替换 | `02_template` 请求的 system 消息 |
| 知识库检索 | 三种检索方式，最多选取 4 条本班切片 | `03_knowledge`；无关章节未发送 |
| 内置与上传 Skill | 内置技能、上传 SKILL.md、绑定与执行 | `05_skill_bound` / `06_skill_active` / `07_uploaded_skill` |
| 工具与 MCP | 安全计算器、独立课程 MCP HTTP 服务 | `08_calculator` / `09_mcp` 的完整往返记录 |

最终报告在 `output/pdf/`。五个问题的逐项验证说明见 [中期验收说明](docs/midterm/README.md)。原始请求/响应在 `docs/midterm/traces.json`，验收结论在 `docs/midterm/verification.json`。这些公开证据只使用课程样例，不包含账号口令、Cookie 或模型网关密钥；运行中的个人追踪记录仅本人可读。

## 一键准备与运行

```sh
python3 scripts/setup_env.py
docker compose build
docker compose run --rm --no-deps api python scripts/warm_model.py
docker compose up -d
```

打开 <http://127.0.0.1:8084>。首次下载嵌入模型需要网络。四个账号 teacher1/student1/teacher2/student2 的口令为本地 `.env` 中的 `DEMO_PASSWORD`。教师可以上传本班材料、模板和技能；学生只读。退出、会话过期、跨班与跨用户记录访问均由后端校验。

当前默认 `LLM_PROVIDER=mock`，便于无密钥环境重现中期验收；其响应为确定性模拟，验证的是消息组装、上下文选择、技能加载和工具闭环，不代表真实大模型生成质量。知识库嵌入、MySQL、Qdrant、计算器和 MCP HTTP 通信均真实运行。正常应用界面不展示测试标签，实际 provider 保留在追踪与报告中。

如需真实模型，在 `.env` 配置 `LLM_PROVIDER=gateway` 以及 `CHAT_BASE_URL`、`CHAT_API_KEY`、`CHAT_MODEL`，然后 `docker compose up -d --force-recreate api`。授权头只在后端发送，不进入追踪。真实网关尚未进行在线验收。

Compose 内置 MCP 服务不映射宿主端口。API 通过 `MCP_URL=http://mcp:8090/mcp` 接入；可在 Compose 的 API 环境配置中改为兼容服务地址。当前支持 2025-03-26 的无状态、JSON 响应 MCP 子集，只允许只读 `course_deadline` 工具。未开放任意远程命令、未支持 stdio/SSE 恢复或全部 MCP 能力。

```sh
# 自动化安全/业务测试
docker compose exec api python -m pytest -q
# 真实 HTTP / MySQL / Qdrant / MCP 验收及证据生成
docker compose exec api python scripts/verify_midterm.py
# 或在宿主机 .venv 中运行以直接写入本仓库 docs/midterm
.venv/bin/python scripts/verify_midterm.py
```

注意：容器内生成的证据位于容器 `/srv/docs/midterm`，可用 `docker compose cp api:/srv/docs/midterm/. docs/midterm/` 导出。验收脚本会向演示班级写入样例模板、知识材料与技能。数据卷持久化；停止系统使用 `docker compose down`，保留卷。

## 代码结构

`app/platform.py` 负责应用、模板、Skill、上下文组装、受限工具循环和追踪；`app/platform_llm.py` 负责模型适配；`app/platform_tools.py` 负责计算器和 MCP 客户端；`app/mcp_server.py` 为独立 MCP 服务；`app/models.py` 的 `platform_records` 持久化模板、技能、对话与追踪。旧版检索模块保持独立。

---

## 第四课历史说明

以下为第四课交付时的范围与演示记录；当时的“不做 Skill/MCP”已由上面的中期版本扩展。

开发仓库：[NicoXDav/campusclaw-course-project](https://github.com/NicoXDav/campusclaw-course-project) · [GitHub新建与提交教程](docs/GitHub新建仓库与提交教程.md)

**价值**：在本班教学材料中找到可核验的知识，降低逐份翻阅资料的成本。  
**场景**：教师上传讲义 → 系统切分并建立向量索引 → 学生检索 → 打开段落出处；配置生成网关后可得到带引用短回答。  
**不做**：跨班检索、超级管理员、PDF/OCR、流式多轮对话、作业流程、MCP（属于后续课程）。

第四次课的主要交付：[变更说明](openspec/changes/add-traceable-vector-retrieval/proposal.md)、[技术设计](openspec/changes/add-traceable-vector-retrieval/design.md)、[验收规约](openspec/changes/add-traceable-vector-retrieval/specs/knowledge-retrieval/spec.md)、[任务状态](openspec/changes/add-traceable-vector-retrieval/tasks.md)。

先读：[第2/3/4课要求总结](docs/课程2-3-4要求总结.md) · [API说明](docs/API.md) · [验收记录](docs/验收记录.md) · [第四课提交说明](docs/第四课提交说明.md)。

## 启动（标准方式）

需要Docker及Compose。首次需下载容器镜像和真实中文嵌入模型，网络速度影响准备时间。

```sh
python3 scripts/setup_env.py
docker compose build
# 首次先缓存模型，避免下载时间占用Web进程的启动超时
docker compose run --rm --no-deps api python scripts/warm_model.py
docker compose up -d
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

短回答默认使用本地抽取式节省模式：只从检索命中的原文中选取相关句子并附引用，不调用外部模型。如需生成式回答，可另外配置兼容`/chat/completions`的真实生成网关：

```dotenv
CHAT_BASE_URL=https://课程提供的地址/v1
CHAT_API_KEY=在本地填写
CHAT_MODEL=课程提供的聊天模型名
```

运行`docker compose up -d --force-recreate api web`应用环境配置。Base URL不要重复写`/chat/completions`或`/embeddings`。无生成网关时，三种检索、溯源和本地抽取式短回答仍可用；页面会如实标注“本地节省模式”，不把摘录伪装为生成模型。

## 验证

```sh
# 容器内运行确定性权限/失败路径测试（测试使用隔离SQLite与测试桩）
docker compose exec api python -m pytest -q
# 实际MySQL、Qdrant、中文模型的HTTP端到端测试
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/e2e.py
# 演示环境专用：短暂停Qdrant并down/up检查持久性，不删卷
.venv/bin/python scripts/verify_operations.py
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
