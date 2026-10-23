"""Build the submission PDF from reproducible HTTP acceptance artifacts."""
import json
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'docs/midterm'
TRACE=json.loads((DATA/'traces.json').read_text())
VERIFY=json.loads((DATA/'verification.json').read_text())
OUT=ROOT/'output/pdf/个人项目阶段性验收-2601210437-孙翌程.pdf'
OUT.parent.mkdir(parents=True,exist_ok=True)
FONT_PATH=Path('/System/Library/Fonts/Supplemental/Arial Unicode.ttf')
if not FONT_PATH.exists():
    raise RuntimeError('请设置可嵌入的中文 TrueType 字体路径 FONT_PATH')
pdfmetrics.registerFont(TTFont('CN',str(FONT_PATH)))
INK=colors.HexColor('#26372F');WINE=colors.HexColor('#80263B');MUTED=colors.HexColor('#6C7A70');LINE=colors.HexColor('#DDE3D8')
ST={
 'title':ParagraphStyle('title',fontName='CN',fontSize=24,leading=33,textColor=INK,spaceAfter=14),
 'h1':ParagraphStyle('h1',fontName='CN',fontSize=18,leading=25,textColor=INK,spaceAfter=12),
 'h2':ParagraphStyle('h2',fontName='CN',fontSize=12,leading=19,textColor=WINE,spaceBefore=10,spaceAfter=7),
 'body':ParagraphStyle('body',fontName='CN',fontSize=9,leading=15,textColor=INK,spaceAfter=7),
 'small':ParagraphStyle('small',fontName='CN',fontSize=7.6,leading=12,textColor=MUTED,spaceAfter=4),
 'th':ParagraphStyle('th',fontName='CN',fontSize=8,leading=12,textColor=colors.white),
 'code':ParagraphStyle('code',fontName='CN',fontSize=7.3,leading=11,textColor=INK,backColor=colors.HexColor('#F0F3EC'),borderPadding=8,spaceAfter=12),
 'note':ParagraphStyle('note',fontName='CN',fontSize=9,leading=15,textColor=INK,backColor=colors.HexColor('#F2F1EB'),borderPadding=9,spaceBefore=8,spaceAfter=12)
}
S=[]
def p(text,style='body'):
    return Paragraph(escape(str(text)).replace('\n','<br/>'),ST[style])
def add(text,style='body'):
    S.append(p(text,style))
def code(value):
    add(json.dumps(value,ensure_ascii=False,indent=2) if not isinstance(value,str) else value,'code')
def table(rows,widths):
    obj=Table([[p(x,'th' if i==0 else 'small') for x in row] for i,row in enumerate(rows)],colWidths=[x*mm for x in widths],repeatRows=1,hAlign='LEFT')
    obj.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),WINE),('GRID',(0,0),(-1,-1),.4,LINE),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F8F9F5')])]))
    S.append(obj)
def shot(name,caption):
    path=ROOT/'screenshots'/name
    if path.exists():
        from PIL import Image as PILImage
        w,h=PILImage.open(path).size
        S.append(Image(str(path),width=145*mm,height=145*mm*h/w))
        add(caption,'small')
def page(title):
    if S:S.append(PageBreak())
    add(title,'h1')
def footer(c,doc):
    c.saveState()
    c.setFont('CN',7.5);c.setFillColor(MUTED);c.setStrokeColor(LINE)
    c.line(20*mm,282*mm,190*mm,282*mm)
    c.drawString(20*mm,286*mm,'CampusClaw / 个人项目阶段性验收')
    c.drawRightString(190*mm,286*mm,'孙翌程 · 2601210437')
    c.line(20*mm,15*mm,190*mm,15*mm)
    c.drawString(20*mm,10*mm,'2026-10-23  |  Git 仓库、代码、追踪记录与报告相互对应')
    c.drawRightString(190*mm,10*mm,str(doc.page))
    c.restoreState()

add('CampusClaw\n个人 AI 应用平台阶段性验收报告','title')
add('孙翌程  |  2601210437  |  2026-10-23','small')
add('仓库：https://github.com/NicoXDav/campusclaw-course-project','body')
add('项目简介','h2')
add('CampusClaw 面向课程学习和个人项目实践，将多个 AI 应用、提示词模板、班级知识库、声明式 Skill 与外部 MCP 工具整合在一个平台。系统在每轮对话保留模型请求、返回、知识证据及工具执行记录，使回答与执行过程可以复核。')
table([['阶段要求','实现'],['多个 AI 应用','学习规划助手、课程知识助手、效率工具助手'],['提示词模板','内置模板、教师自定义模板、{{question}} 变量替换'],['知识库检索','MySQL + Qdrant，关键字/向量/混合检索与原文引用'],['Skill 技能','内置技能、SKILL.md 上传、绑定元数据与执行正文分离'],['外部工具与 MCP','安全计算器、独立 HTTP MCP 服务、工具调用闭环']], [43,127])
S.append(Spacer(1,7*mm));shot('midterm-platform.jpg','图 1  平台首页与技能执行：三个应用、对话区和上下文配置共同呈现。')
add('验收环境说明：本次无可用聊天模型密钥，LLM 适配层使用确定性模拟接口，检验请求组装与工具闭环。MySQL、Qdrant、真实中文嵌入、计算器和 MCP HTTP 通信均实际运行。报告不把模拟回答作为真实模型在线生成质量的证据。','small')

page('01 / 系统结构与数据边界')
table([['层次','职责与代码'],['界面层','templates/platform.html + static/platform.js/css：应用、对话、模板、技能与追踪'],['编排层','app/platform.py：认证、选取上下文、技能加载、受限工具循环、持久化追踪'],['模型适配','app/platform_llm.py：mock / gateway，兼容 chat/completions 消息结构'],['知识库','app/retrieval.py + providers.py：切片、真实嵌入、SQL 回表、班级过滤与引用'],['工具层','platform_tools.py：AST 四则运算、MCP 发现/调用；mcp_server.py：独立只读服务'],['存储层','MySQL 中的 platform_records 保存模板、技能、对话和追踪；Qdrant 存向量']], [35,135])
add('每次对话的处理顺序','h2')
for n,line in enumerate(['从 HttpOnly Cookie 验证随机 Token，读取用户角色与 class_id。','根据应用规则选择模板，替换变量；从已绑定技能中加载元数据。','按需在本班检索最多 4 条证据；只有显式执行时加载选中 Skill 正文。','加入最近 12 条历史消息与本轮 user 消息，附上启用工具的定义。','调用适配层；如返回 tool_calls，校验工具名及参数，执行并回传结果。','最多允许 4 轮工具循环，保存最终回答、引用、完整请求/返回与失败记录。'],1):
    add(f'{n}. {line}')
add('认证与隔离','h2')
add('登录签发 32 字节随机 Token；数据库只存 SHA-256 哈希，8 小时过期，登录轮换旧会话。教师可上传技能和模板，学生写入返回 403；材料按班级隔离，追踪和对话同时按本人及班级隔离。客户端传入的 system 消息与 class_id 不作为权限或系统规则。')
add('安全约束','h2')
add('上传只接受 UTF-8 Markdown，最大 32 KiB，不运行上传的 shell/Python。计算器使用 AST 白名单并限制长度、节点数与数值范围。MCP 地址来自服务端配置，工具和参数须在白名单内；服务不直接暴露宿主端口，Origin 检查拒绝跨站访问。')

page('02 / 验证一：模型请求、返回与提示词模板')
add('结论：模板随每轮请求传入，位于 system 消息；原始用户提问仍保留在 user 消息中。','note')
t=TRACE['02_template'];req=t['rounds'][0]['request'];res=t['rounds'][0]['response']
add('方法：对照 01_plain 与 02_template，只切换提示词模板。保存的请求关键字段如下（完整内容见 traces.json）：')
code(req)
add('对应返回','h2');code(res)
add('参数含义','h2')
add('model 指定适配层模型；messages 按 system、最近历史、当前 user 排列；temperature=0、max_tokens=800、stream=false 为实际传入值。启用工具时额外传 tools 与 tool_choice=auto。模拟接口不做真实 token 计费，usage 内为 null；不得将字符数当作 token 数。')
add('验证证据：verification.json 中“模板原文经变量替换进入 system”“模板不改变原始 user 消息”均通过。')

page('03 / 验证二：知识库是否全量发送')
t=TRACE['03_knowledge'];evidence=t['evidence']
add('结论：不发送知识库全部内容。先检索，最多取 4 条本班 ready 切片，将标题、编号、chunk_id 与命中文本放入 EVIDENCE。','note')
add('实验准备','h2');add('上传“中期验收知识库.md”，其开头包含借阅规则，另外包含 12 个独立无关章节。使用 hierarchy 切分，经过真实中文嵌入后写入 Qdrant；以“借阅期限”执行关键字检索，避免把语义近似误当作无命中。')
table([['项','实际结果'],['问题',t['query']],['命中条数',str(len(evidence))+'（限制 4）'],['发送证据正文长度',str(sum(len(h['excerpt']) for h in evidence))+' 字符'],['无关章节标记','NEVER_SEND_ALL_11 未进入模型请求'],['整库原文/向量','未作为 LLM 请求字段'],['跨班材料','班级过滤与 SQL 回表校验后不可见']], [53,117])
add('命中与出处','h2')
table([['编号','材料','位置'],*[[str(i),h['title'],f"段 {h['chunk_index']}，字符 [{h['start_offset']}, {h['end_offset']})"] for i,h in enumerate(evidence,1)]],[15,86,69])
add('发送给模型的一个证据对象（摘录）','h2')
h=evidence[0];code({'citation':1,'title':h['title'],'chunk_id':h['chunk_id'],'text':h['excerpt'][:450]})
add('无命中验证','h2');add('04_no_evidence 使用在资料中不存在的查询“龘靐齉爩”，返回“资料中未找到相关内容”。中文全文检索采用 ngram，因此不能用含有“验收”等常见词的句子假设一定无命中；实验已根据实际索引行为选取独立输入。')

page('04 / 验证三、四：Skill 加载与执行逻辑')
add('结论：绑定只传技能目录元数据；执行时才传选中技能的完整 Markdown 正文。声明式 Skill 指导回复，不直接执行上传代码。','note')
table([['状态','LLM 请求包含','不包含'],['绑定但未执行','SKILL_CATALOG：id、name、description','技能正文及其他本机文件'],['执行一个已绑定技能','目录 + 该技能 SKILL_BODY_START/END 正文','其他未执行技能的正文'],['上传后执行','经校验、入库后的技能正文','任意脚本执行权限']], [34,78,58])
add('请求对照','h2')
bound=TRACE['05_skill_bound']['rounds'][0]['request']['messages'][0]['content']
active=TRACE['06_skill_active']['rounds'][0]['request']['messages'][0]['content']
code('绑定请求：\n'+bound+'\n\n执行请求新增：\n'+active.split('SKILL_BODY_START')[1].split('SKILL_BODY_END')[0])
add('执行路径','h2')
for i,line in enumerate(TRACE['06_skill_active']['skill_steps'],1):add(f'{i}. {line}')
add('上传技能验证','h2');add('将 examples/SKILL.md 上传到技能库，返回 201，并出现在本班目录。07_uploaded_skill 在绑定后显式执行，模型请求包含“课程项目验收清单”完整正文。上传支持单个 .md 文件，不宣称支持 ZIP、附带资源或外部脚本。')
add('声明式执行的边界','h2');add('本次模拟接口验证的是“选择、加载、传递、追踪”路径；技能对真实模型推理与输出质量的作用，需要接入真实网关另行评估。Skill 中的文字不赋予额外文件、网络或命令权限。')

page('05 / 验证五：MCP 工具参数与结果回传')
t=TRACE['09_mcp']
add('结论：首轮将工具元数据转换为 function 定义传入 tools。模型返回 tool_calls 后，由后端调用 MCP；第二轮 messages 包含 assistant 工具调用和 role=tool 的真实工具结果。','note')
add('真实 HTTP 往返','h2')
table([['步骤','请求方法','结果'],*[[str(i),e['request']['method'],str(e['http_status'])] for i,e in enumerate(t['mcp_events'],1)]],[20,110,40])
add('首轮 LLM 请求附带的工具定义','h2');code(json.dumps(t['rounds'][0]['request']['tools'],ensure_ascii=False))
add('模型返回的工具调用','h2');code(json.dumps(t['rounds'][0]['response']['choices'][0]['message']['tool_calls'],ensure_ascii=False))
add('MCP tools/call 实际参数','h2');code(t['mcp_events'][-1]['request'])
add('第二轮回传与最终结果','h2')
add('第二轮保留首轮 messages 并追加 role=assistant 的 tool_calls、role=tool 的返回内容，使用同一 tool_call_id 关联。返回包含截止时间 2026-10-28 00:00 Asia/Shanghai、交付物和教师要求来源。完整的 RPC 返回与两轮 LLM 参数在 09_mcp 中保留。')
add('支持范围：独立 HTTP MCP 服务、2025-03-26 协议、无状态 JSON 响应子集。当前只读工具 course_deadline 处于白名单；不是支持任意未知 MCP 工具的通用执行器。')

page('06 / 自动化与实际服务验收')
unit=(DATA/'unit-tests.txt').read_text() if (DATA/'unit-tests.txt').exists() else '测试输出待生成'
add('自动化回归','h2');code(unit[-550:])
add('真实 HTTP 验收：'+str(sum(r['passed'] for r in VERIFY['results']))+' / '+str(len(VERIFY['results']))+' 项通过。模型适配为 mock；数据库、嵌入、向量库和 MCP 均为实际服务。')
table([['编号','验收项','结果'],*[[str(i),r['name'],'通过' if r['passed'] else '失败'] for i,r in enumerate(VERIFY['results'],1)]],[14,137,19])
add('覆盖未登录、学生写入、跨班/跨用户记录访问、非法类型、无效算式、未绑定技能执行、客户端 system 注入、工具失败留痕等路径。','small')

page('07 / 部署复现、交付与边界')
add('仓库地址','h2');add('https://github.com/NicoXDav/campusclaw-course-project')
add('部署','h2');code('python3 scripts/setup_env.py\ndocker compose build\ndocker compose run --rm --no-deps api python scripts/warm_model.py\ndocker compose up -d')
add('打开 http://127.0.0.1:8084，使用 teacher1/student1/teacher2/student2；口令从本地 .env 的 DEMO_PASSWORD 获取，不公开在仓库或报告。首次运行需下载嵌入模型，后续复用持久化缓存。')
add('证据与测试复现','h2');code('docker compose exec api python -m pytest -q\n.venv/bin/python scripts/verify_midterm.py\n# 原始证据：docs/midterm/traces.json、verification.json\n# 页面截图：screenshots/midterm-*.jpg')
add('本阶段的实现范围','h2')
add('已实现并验证：应用入口、模板入库和传递、本班检索、技能上传与渐进加载、真实计算与 MCP 往返、对话持久化和本人可见的请求追踪。所有样例记录只包含课程演示数据；Cookie、账号口令和 Authorization 不写入追踪。')
add('真实大模型在线生成尚未验收：本次按用户提供的无密钥条件使用模拟适配。切换真实模型需要在 .env 设置 LLM_PROVIDER=gateway、CHAT_BASE_URL、CHAT_API_KEY、CHAT_MODEL，然后重建 API 容器。真实模型可能产生不同工具调用和引用，仍需单独复核。')
add('MCP 实现限定为当前只读白名单和 JSON 响应子集；不包含通用 stdio、SSE 流恢复、任意远程命令。单实例适合课程展示；多实例限流共享、自动历史摘要与真实模型质量评测属于后续扩展。')
add('复核修正','h2');add('联调发现并修正了追踪详情序列化错误、非法参数类型处理、失败工具记录缺失、API 重建后的 Nginx 地址更新问题。无命中实验依据实际 ngram 索引行为调整；测试结果保存为可复现文件，未以截图上的固定成功标志代替实际接口检查。')
add('参考规范','h2');add('MCP HTTP Transport (2025-03-26):\nhttps://modelcontextprotocol.io/specification/2025-03-26/basic/transports\nMCP Tools (2025-03-26):\nhttps://modelcontextprotocol.io/specification/2025-03-26/server/tools','small')

doc=SimpleDocTemplate(str(OUT),pagesize=A4,rightMargin=20*mm,leftMargin=20*mm,topMargin=23*mm,bottomMargin=22*mm,
    title='CampusClaw 个人项目阶段性验收报告',author='孙翌程 2601210437')
doc.build(S,onFirstPage=footer,onLaterPages=footer)
print(OUT)
