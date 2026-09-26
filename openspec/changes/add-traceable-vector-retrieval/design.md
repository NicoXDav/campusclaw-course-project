# 技术设计与决策

## Context
课程网页核对日期：2026-09-26。第二课用 Flask + SQLite 举例，第三、四课当前教程的讲师实现使用 Go + MySQL。已有个人第三课代码为 Flask + SQLite。保留 Python 语言和前端基础，采用 MySQL 与 Qdrant，行为严格以本 change 为契约；不是照搬讲师代码。

## Goals / Non-Goals
目标是可验证的本班检索和可追溯短回答。非目标见 proposal。

## Decisions
1. Flask + SQLAlchemy + MySQL 8.4；正文与切片保存在关系库，FULLTEXT WITH PARSER ngram，ngram_token_size=2。SQLite 仅作为单元测试适配器，其关键字近似实现不代替 MySQL 全文集成验收。
2. Qdrant 集合 campusclaw_chunks，Cosine。point.id = knowledge_chunks.id；payload 仅 class_id/material_id/knowledge_entry_id/chunk_id/chunk_index。正文必须按 point.id 和会话班级回表，不能信任 payload 文本或标识。
3. 默认本地 FastEmbed BAAI/bge-small-zh-v1.5（512 维真实中文模型，无须密钥）；也支持兼容 /embeddings 网关。800 字片段进一步按模型 token 窗口分块并平均归一化，避免截断尾部。更换模型或维度必须重建独立集合及所有索引。
4. 服务端随机会话 token，数据库只存 token 哈希；8 小时到期，登录成功注销旧会话，Cookie HttpOnly/SameSite=Lax。角色和 class_id 每次从数据库读取。写 API 校验 Origin（有值时必须同源）。密码采用 Werkzeug scrypt，种子口令只从环境读取。
5. 上传验证扩展名、2 MiB、UTF-8、非空和 NUL；文件重命名在两表事务提交前完成，异常回滚并清理文件。正文提交后才索引；嵌入失败不能撤销原文。跨 MySQL/Qdrant 无分布式事务：先将材料标为 pending、清旧向量和旧切片，写 pending 新片段；全部嵌入验证后批量写向量，成功才 ready。失败标 failed 并尽力清理向量；搜索只回表 ready 行，因此残留向量不可见。下次重建按 material_id 清理。
6. 单 worker + 多线程，材料索引使用进程锁串行化，规避同一材料并发重建；不宣称多进程安全。启动补索引仅补没有切片的 seed 材料，失败留给教师显式重试，不每次重启重切。
7. auto 为 800 字/80 重叠，优先空行、换行、句号；custom 长度 100–2000、重叠比例 0–0.5、分隔符和可选清洗；hierarchy 识别 #/##/### 标题，保留标题，超长章节用 auto。字符范围为 Python Unicode codepoint 的 0-based [start,end)，段号 1-based。预处理不改原文，偏移明确标为 processed，溯源同时返回切分文本，前端不拿 processed 偏移高亮原文。
8. keyword 仅查 ready 切片且 SQL 班级过滤，全文分>0；vector 余弦>=0.35，Qdrant 前置班级过滤并 SQL 二次过滤；hybrid 两路各取前50并按 1/(60+rank) 融合。最终 top_k 1–20，默认6，ask 固定前4。向量/混合依赖失败返回503，不悄悄降级；keyword 不访问嵌入或 Qdrant。
9. ask 仅用最新问题检索；不接纳客户端 system 或历史权限声明。零命中直接固定句；有命中调用 CHAT_BASE_URL/chat/completions，服务端编号证据。要求返回 answer 和引用编号 JSON，校验编号属于当前命中；非法引用/网关失败为502/503，绝不伪造来源。模型能否正确蕴含答案仍须人工核对；引用有效性不能证明事实蕴含。未配置生成网关时有依据的 ask 明确503，检索仍完整可用。
10. Compose: web/api/db/qdrant，只有 web 绑定 localhost:8084；数据库、文件、向量、模型缓存持久化。/health 检查 SQL，/api/status 报告检索依赖与生成配置。Qdrant 故障不让健康检查误杀可用的关键字服务。

## Risks / Trade-offs
- 本地模型初次需要下载约90MB权重及分词器；离线环境须预热缓存。课程网关可替换。模型阈值0.35遵循课件，但相似度不等于事实相关性，README 提供无关查询实测。
- 本次是课程单实例；同步索引处理大文件可能慢，前端明确等待。异步任务留后续课。
- 若写向量后 DB 提交失败，残留不可检索且重建清理，避免假装跨库原子事务。
- 基线保存在 openspec/specs/auth-upload；第四课 delta 不提前合并。旧资料原样留在原工作目录。

## Migration Plan
新建独立课程仓库和 Compose 数据卷；不读取或复制既有个人数据库/上传文件。初始化双班四账号与区分语料，执行规约验证、自动测试、Compose E2E 和重启持久性检查。

## Open Questions
远端仓库账号/可见性及真实课程生成网关配置待用户提供；不影响规约、源码和本地检索开发。
