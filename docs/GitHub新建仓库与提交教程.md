# GitHub新建仓库与提交作业

本次作业仓库：https://github.com/NicoXDav/campusclaw-course-project

## 1. 新建仓库

1. 登录GitHub，点击右上角“+” → New repository；也可在首页点击New。
2. Owner选择自己的账号NicoXDav。
3. Repository name填写英文名称，例如campusclaw-course-project。
4. Description填写项目用途。课程作业选择Public，老师无需申请权限即可查看；如选Private，需要额外邀请老师。
5. 本地已有完整项目时，不勾选Add README，不另选.gitignore或license，避免和本地版本重复。
6. 点击Create repository，得到仓库页面地址。

## 2. 网页上传（不要求安装Git）

1. 新仓库点击uploading an existing file；已有文件的仓库选择Add file → Upload files。
2. 上传项目源码，保留app、openspec、docs等目录结构。首页应能直接看到README.md，不能只上传一个压缩包。
3. 不上传.env、数据库、上传的私人材料、.venv、node_modules或模型缓存。.env.example是配置示例，可以上传。
4. 在Commit changes处填写说明，例如“完成第四课本班可追溯知识库检索”。选择直接提交到main，点击Commit changes。
5. 刷新仓库，检查README、代码和OpenSpec四件套是否能打开。

## 3. 后续用Git提交（推荐）

Safari登录状态与Git命令行凭据是两回事。命令行首次推送需要配置GitHub认证（例如GitHub Desktop正常登录）；GitHub账号密码不能直接作为HTTPS推送密码。

本机已准备GitHub官方CLI，路径为`~/.local/bin/gh`。首次认证可运行：

```sh
~/.local/bin/gh auth login --hostname github.com --git-protocol https --web
~/.local/bin/gh auth setup-git
```

按提示在浏览器完成一次性代码验证与授权，不要把令牌写到代码或发给别人。

本次项目已经在`/Users/sunyicheng/Documents/homework/campusclaw`，后续直接进入此目录修改，不需要重新创建仓库。首次把已有本地项目关联空仓库时，通常执行：

```sh
# 本次项目已完成初始化、提交和远端关联，无需重复这些准备步骤
git remote add origin https://github.com/NicoXDav/campusclaw-course-project.git
git push -u origin main
```

在另一台电脑使用已有仓库时，先克隆一次：

```sh
git clone https://github.com/NicoXDav/campusclaw-course-project.git
cd campusclaw-course-project
```

在克隆目录修改文件后：

```sh
git status
git add README.md app openspec docs
git commit -m "说明这次修改了什么"
git push origin main
```

- git status：查看哪些文件变了。
- git add：选择这次提交的文件；不要把密钥加入提交。
- git commit：保存本地版本与说明。
- git push：把本地提交上传到GitHub。只有commit、没有push，老师看不到新版本。

多人协作或另一台电脑改过代码时，先git pull --rebase，解决冲突后再push；不要用强制推送覆盖别人的工作。

## 4. 给老师交作业

通常提交仓库主页地址即可：

https://github.com/NicoXDav/campusclaw-course-project

老师从README进入，重点查看openspec/changes/add-traceable-vector-retrieval/下的proposal.md、design.md、tasks.md和specs/目录。也可附上docs/第四课提交说明.md的链接。

仓库公开只代表代码可访问，不代表已向老师发送邮件。收件邮箱和邮件发送属于单独的递交动作。
