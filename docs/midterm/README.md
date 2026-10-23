# 个人项目阶段性验收

作者：孙翌程，2601210437。日期：2026-10-23。

## 项目介绍

CampusClaw 是带班级数据隔离的个人 AI 应用平台。提供学习规划、课程知识和效率工具三个应用，支持提示词模板、知识检索、声明式 Skill 的上传与渐进加载、工具调用以及独立 MCP 服务接入。平台把每次请求的参数、返回、引用和工具执行结果保存为本人可读的追踪记录。

本次经用户确认使用无密钥模拟 LLM。所有 `traces.json` 中 provider 为 mock 的结果均为模拟返回；没有将其表述为真实模型在线生成。数据库、中文嵌入、向量库、HTTP、工具执行及 MCP 往返真实运行。模型网关适配已实现，但未做真实在线验收。

## 五个问题及验证方法

1. **每次对话参数和返回是什么，模板会传递吗？** 查看 `01_plain` 与 `02_template`。请求明确包含 model、messages、temperature=0、max_tokens=800、stream=false；启用工具另含 tools、tool_choice=auto。system 放应用规则、替换变量后的模板及所选上下文；最多保留最近 12 条历史消息。response 保留 choices/message、finish_reason、usage，模拟 provider 的 token 数为 null，不伪造计费。模板进入 system，原始提问仍为 user 消息。
2. **绑定知识库会发送全部内容吗？** `03_knowledge` 在本班 ready 切片中检索，最多取 4 条，仅将编号、标题、chunk_id 和片段文本放入 EVIDENCE；不发送完整材料、向量或其他班内容。样例材料含 12 个无关章节，`NEVER_SEND_ALL_11` 未出现于模型请求。`04_no_evidence` 验证明确无命中。
3. **绑定 Skill 会包含全部内容吗？** `05_skill_bound` 仅含 SKILL_CATALOG 的 id/name/description；不含正文。`06_skill_active` 才把选中技能完整 Markdown 正文放入 SKILL_BODY_START/END。不是所有绑定技能一起发送，也不自动扫描本机技能目录。
4. **执行 Skill 的逻辑？** 解析元数据、检查班级/绑定、读取被执行正文、按指令进行回复、记录步骤和请求。`07_uploaded_skill` 验证上传后可以执行。技能是声明式提示指令，不是任意 Python/shell 执行；本版本上传单个 UTF-8 .md，不宣称支持 ZIP 中脚本或附件执行。
5. **MCP 接入后发送什么？** `09_mcp` 展示 initialize → notifications/initialized → tools/list → tools/call。首轮向模型发送转成 function 格式的工具名、描述、JSON Schema；模型返回 tool_calls 后，由后端校验工具/参数白名单并发起 RPC；把 assistant tool_calls 和 role=tool 的真实结果追加到下一轮 messages。模型不会获得整个 MCP 服务源码或网关密钥。

## 证据索引

- `verification.json`：真实 HTTP 验收条目与结果。
- `traces.json`：11 组受控课程样例，按编号对应上面各问题。
- `unit-tests.txt`：自动化回归输出。
- `review.md`：代码审查、问题修正和边界。
- 仓库 `screenshots/midterm-*.jpg`：浏览器实测。
- 仓库 `output/pdf/`：可提交的 PDF 报告。

## 可复现演示

1. 登录后在学习助手选择“项目验收”模板，绑定并执行 project-review。
2. 切换课程知识助手，输入“借阅期限”，查看引用，再打开原文。
3. 在“模板与技能”上传 `examples/SKILL.md`，返回对话绑定并执行。
4. 在效率工具助手输入“计算 12*(3+4)”，结果为 84。
5. 勾选课程 MCP，检查连接，提问“个人项目中期验收截止时间是什么？”。
6. 打开本轮请求记录，检查两轮请求、tool_calls 与 role=tool 回传内容。

参考协议：[MCP 2025-03-26 HTTP 传输](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports)、[MCP Tools](https://modelcontextprotocol.io/specification/2025-03-26/server/tools)。本项目选择其中无状态 JSON 返回子集。
