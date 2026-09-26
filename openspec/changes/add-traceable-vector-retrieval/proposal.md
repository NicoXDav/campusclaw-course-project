# 第四次课变更：本班可追溯知识库检索

## Why
第三课已解决登录、角色权限、班级隔离与材料上传，但学生仍须逐份打开资料找答案。本变更让教师和学生只在本班知识库中查找相关片段，并用标题、段号、字符范围及原文链接核实来源。无证据不生成回答。

## What Changes
- 上传后的正文经过自动、自定义或 Markdown 标题切分，写入 knowledge_chunks，再嵌入并写入 Qdrant。
- 增加 keyword、vector、hybrid 检索，默认 hybrid；向量余弦阈值 0.35，RRF k=60。
- 每条命中返回材料标题、切片主键、段号、字符范围、摘录、原文链接、两路分数及名次。
- 所有查询从服务端会话获取班级；SQL、Qdrant 和向量回表均独立过滤。
- 增加教师重建索引及 ready/failed/pending 状态；失败保留材料，支持重试。
- 增加有依据才调用兼容网关的简短问答；无命中固定响应，citations 为空。
- 补齐现有第三课实现的会话到期、原子上传、环境配置、容器健康检查和自动化验收。

## Capabilities
### New Capabilities
- `knowledge-retrieval`: 本班切分、向量入库、三路检索、内容溯源、短回答和索引重建。
### Modified Capabilities
- `auth-upload`：补齐最新第三课教程的失败响应同形、口令验证等时处理与登录限流；内部存储由 SQLite 升级为 MySQL，既有个人作业数据不自动迁移、不上传。

## Impact
后端延续 Flask，以 MySQL + Qdrant 对齐当前课件的存储链路。Compose 仅 Nginx 暴露宿主端口。复用第三课界面基础并增加检索页；源码、规约、测试和运行说明在同一仓库。

## Non-goals
不做跨班检索、平台超级管理员、注册找回密码、PDF/Word/OCR、流式长对话、多轮记忆、作业提交、MCP、重排序或生产高可用。后续课的智能体/技能/MCP 不属于本次第四课交付。

## Acceptance
以 specs/knowledge-retrieval/spec.md 的场景和 tests/ 验收。规约 CLI 校验不等于功能测试。保留本 change 供第四课作业审阅；验收前不归档。
