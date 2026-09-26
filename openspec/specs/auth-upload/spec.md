# auth-upload

## Purpose
保留第三课已实现的教师与学生登录、本班材料读写和文件下载的行为基线，第四课检索继承同一权限边界。

## Requirements

### Requirement: 会话与权限
系统 MUST 提供教师与学生账号密码登录并以服务端会话判定角色和班级。

#### Scenario: 未登录接口
- **WHEN** 未登录用户请求受保护API
- **THEN** 系统 MUST 返回401且无业务数据

#### Scenario: 学生上传
- **WHEN** 学生提交上传
- **THEN** 系统 MUST 返回403且无写入

### Requirement: 班级材料
系统 MUST 只向登录者提供本班数据库材料；跨班和不存在均为404。

#### Scenario: 跨班读取
- **WHEN** A班请求B班材料详情或下载
- **THEN** 系统 MUST 返回404且不泄露标题和正文

### Requirement: 正文入库
系统 MUST 允许教师上传UTF-8的txt/md文件，在同一事务写入materials与knowledge_entries，文件不静态公开。

#### Scenario: 正常上传
- **WHEN** 教师提交合法非空且不超过2MiB的文本
- **THEN** 系统 MUST 持久保存本班材料和正文，并允许本班学生读取

#### Scenario: 非法文件
- **WHEN** 上传格式非法、超限、空文本或编码非法
- **THEN** 系统 MUST 返回明确4xx且不产生孤立文件或不完整行
