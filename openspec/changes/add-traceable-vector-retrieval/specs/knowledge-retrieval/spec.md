## ADDED Requirements

### Requirement: 切分与偏移

系统 MUST 提供 auto、custom、hierarchy，默认 auto；保留上传原文并明确偏移坐标系。

#### Scenario: 自动窗口

- **WHEN** 省略策略或选择 auto，输入超过800字
- **THEN** 系统 MUST 所有片段不超过800字，相邻窗口最多80字重叠，text[start:end]等于切片，忽略自定义参数

#### Scenario: 自定义清洗

- **WHEN** custom 指定100–2000字、0–50%重叠、分隔符及清洗选项
- **THEN** 系统 MUST 按参数切分，原文保持不变，预处理后偏移标记为processed

#### Scenario: 标题分章

- **WHEN** hierarchy 输入含Markdown三级以内标题且某章超长
- **THEN** 系统 MUST 标题留在本章，超长章节再次自动切分

#### Scenario: 参数无效

- **WHEN** 未知策略、长度或比例越界
- **THEN** 系统 MUST 返回400且不改变已有索引

### Requirement: 索引生命周期

系统 MUST 在正文提交后生成切片并写入真实嵌入和 Qdrant，提供教师重建；失败保留原文。

#### Scenario: 入库成功

- **WHEN** 教师上传合法材料且依赖正常
- **THEN** 系统 MUST 返回201，切片与材料ready，point.id等于chunk.id且payload不含正文

#### Scenario: 失败可恢复

- **WHEN** 嵌入或向量库失败
- **THEN** 系统 MUST 材料正文保留，索引failed，不可搜索半成品；教师重试成功后ready

#### Scenario: 重建清理

- **WHEN** 教师在本班材料上按新策略重建
- **THEN** 系统 MUST 旧切片和旧向量被替换，没有重复结果

#### Scenario: 学生不可重建

- **WHEN** 学生调用重建API
- **THEN** 系统 MUST 返回403，无索引变化

#### Scenario: 跨班不可重建

- **WHEN** 教师请求别班或不存在的material_id
- **THEN** 系统 MUST 均返回相同404

### Requirement: 三种检索

系统 MUST 支持 keyword、vector、hybrid（默认），应用余弦阈值0.35与RRF k=60。

#### Scenario: 关键字独立

- **WHEN** keyword 查询本班原文词
- **THEN** 系统 MUST 仅SQL全文检索ready片段；无嵌入及Qdrant调用

#### Scenario: 向量同义

- **WHEN** vector 查询与本班资料语义相关的改写
- **THEN** 系统 MUST 嵌入后按班级搜索Qdrant，过滤低于0.35候选，按余弦降序回表

#### Scenario: 混合名次融合

- **WHEN** hybrid 两路候选不完全相同
- **THEN** 系统 MUST 按两路各自rank计算RRF，缺席一路不加分，不直接相加原始分数

#### Scenario: 依赖故障

- **WHEN** 向量库或嵌入不可用
- **THEN** 系统 MUST vector/hybrid为503而keyword仍可用

#### Scenario: 查询校验

- **WHEN** 空白或超过1000字查询、无效模式或top_k越界
- **THEN** 系统 MUST 返回400

### Requirement: 本班隔离

系统 MUST 只信任会话班级，SQL与向量查询及回表均过滤，所有API先认证。

#### Scenario: 未登录

- **WHEN** 无有效Cookie调用检索、问答或切片API
- **THEN** 系统 MUST 返回401，无业务数据

#### Scenario: 伪造班级

- **WHEN** A班用户在body/query/header写B班并查询B班专有词
- **THEN** 系统 MUST 不能出现B班标题、切片、向量或引用；无候选为200空集合

#### Scenario: 二次过滤

- **WHEN** 向量存储意外返回其他班的point id
- **THEN** 系统 MUST 关系库回表过滤掉该记录

#### Scenario: 跨班溯源

- **WHEN** A班打开B班切片、材料或下载链接
- **THEN** 系统 MUST 与不存在相同404

### Requirement: 来源可核验

系统 MUST 为每条命中提供从关系库读取的标题、段号、字符范围、摘录、来源链接与分数。

#### Scenario: 点击出处

- **WHEN** 用户打开本班命中的source_url
- **THEN** 系统 MUST 显示对应原文和切片，范围与coordinate_space一致

#### Scenario: 恶意正文

- **WHEN** 材料含HTML或脚本
- **THEN** 系统 MUST 以文本安全展示，不执行脚本

### Requirement: 有据短回答

系统 MUST 只在本班混合检索有候选时调用生成模型，并校验引用归属。

#### Scenario: 无据不生成

- **WHEN** 本班混合检索无候选
- **THEN** 系统 MUST 200，answer为资料中未找到相关内容，citations=[]，生成调用次数为0

#### Scenario: 有据生成

- **WHEN** 命中本班前4条且生成网关可用
- **THEN** 系统 MUST 只发送本班证据和问题，返回短回答及对应[1]等引用，citations与编号一致

#### Scenario: 不信任system

- **WHEN** 客户端提交system消息及class_id
- **THEN** 系统 MUST 服务器不把客户端system传给模型，班级来自会话

#### Scenario: 无效引用

- **WHEN** 模型返回不在所给证据中的编号或未声明引用
- **THEN** 系统 MUST 502且不发布伪造回答

#### Scenario: 网关未配置

- **WHEN** 有候选但CHAT_API_KEY或CHAT_BASE_URL缺失
- **THEN** 系统 MUST 503明确提示配置问题，不冒充模型生成

### Requirement: 部署与持久性

系统 MUST 以Compose启动且只有web映射端口，保留数据库、上传、向量及缓存。

#### Scenario: 健康检查

- **WHEN** 按README启动
- **THEN** 系统 MUST /health为200且可登录，MySQL/Qdrant不直接暴露

#### Scenario: 重启不丢失

- **WHEN** 上传并检索后Compose down再up而不删卷
- **THEN** 系统 MUST 账号、材料、切片、向量与溯源仍可用

