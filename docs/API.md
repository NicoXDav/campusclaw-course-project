# API与数据边界

统一JSON响应，成功含`ok:true`，错误含`ok:false,message`。Cookie `campus_session`携带随机会话token，数据库存其SHA256；有效期8小时。所有业务身份来自服务端用户/会话，body/query/header中的class_id不作为权限依据。

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| POST | /api/login | 公开 | `{username,password}`，成功设置HttpOnly Cookie |
| POST | /api/logout | 任意 | 注销当前token |
| GET | /api/me | 登录 | 当前角色及班级 |
| GET | /api/materials | 登录 | 仅本班列表，含index_status |
| POST | /api/materials | 教师 | multipart file与可选chunk_options JSON字符串；成功201 |
| GET | /api/materials/:id | 本班 | 正文、状态与切分参数 |
| GET | /api/materials/:id/download | 本班 | 鉴权附件下载 |
| POST | /api/materials/:id/reindex | 本班教师 | JSON切分参数，成功200；依赖失败503，保留原文 |
| POST | /api/search | 登录 | `{query,mode:"hybrid",top_k:6}` |
| GET | /api/chunks/:id | 本班 | 原文、切片、预处理文本及偏移 |
| GET | /sources/:id | 本班 | 可读溯源页面 |
| POST | /api/ask | 登录 | `{query}`，固定混合检索前4条 |
| GET | /api/status | 登录 | 向量库状态、生成配置状态，不返回密钥 |
| GET | /health | 公开 | SQL可读为200，无业务内容 |

切分参数（custom才使用其他参数）：

```json
{"strategy":"custom","max_length":800,"overlap":0.1,"delimiter":"\n\n","remove_urls":false,"collapse_whitespace":false}
```

Search命中字段包括`chunk_id/material_id/title/chunk_index/start_offset/end_offset/coordinate_space/excerpt/source_url/material_url/score/keyword_score/keyword_rank/vector_score/vector_rank`。段号从1开始，字符范围为Unicode codepoint从0开始的左闭右开区间；processed坐标只能用于processed_text。不存在的某路分数/名次为null；不能把RRF分当余弦。

401未登录；403学生写入或跨站Origin；404跨班/不存在；400无效输入；413文件超限；415格式不支持；422非UTF-8/空文件/二进制；502模型引用无效；503检索或生成依赖不可用。

上传成功但索引失败仍201且`index_status:"failed"`：表示原文件和正文已可靠保存，教师可修复依赖后重建。向量写入失败期间keyword也不搜索该材料的pending/failed切片，避免半成品结果。
