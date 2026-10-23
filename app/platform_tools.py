"""Small allowlisted local tools and a JSON-only Streamable HTTP MCP client."""
import ast
import math
import operator
import uuid
import requests
from .providers import DependencyError

CALCULATOR = {'type':'function','function':{'name':'calculator','description':'计算基本四则运算',
    'parameters':{'type':'object','properties':{'expression':{'type':'string'}},'required':['expression'],'additionalProperties':False}}}


def calculate(expression):
    if not isinstance(expression,str) or not 1 <= len(expression) <= 120:
        raise ValueError('表达式长度无效')
    ops = {ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv}
    def visit(node):
        if isinstance(node,ast.Constant) and type(node.value) in (int,float):
            value = node.value
        elif isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)):
            value = visit(node.operand) * (-1 if isinstance(node.op,ast.USub) else 1)
        elif isinstance(node,ast.BinOp) and type(node.op) in ops:
            value = ops[type(node.op)](visit(node.left),visit(node.right))
        else:
            raise ValueError('只允许数字、括号和加减乘除')
        if abs(value)>1e12 or not math.isfinite(value):
            raise ValueError('计算结果超出范围')
        return value
    try:
        tree=ast.parse(expression,mode='eval')
        if sum(1 for _ in ast.walk(tree))>80:
            raise ValueError('表达式过于复杂')
        return {'expression':expression,'value':visit(tree.body)}
    except (SyntaxError,ZeroDivisionError,OverflowError,RecursionError) as error:
        raise ValueError('无效计算表达式') from error


class MCPClient:
    def __init__(self,url):
        self.url=url
        self.session=requests.Session()
        self.session.trust_env=False
        self.events=[]

    def rpc(self,method,params=None,notification=False):
        packet={'jsonrpc':'2.0','method':method,'params':params or {}}
        if not notification:
            packet['id']=uuid.uuid4().hex
        headers={'Accept':'application/json, text/event-stream','MCP-Protocol-Version':'2025-03-26'}
        try:
            r=self.session.post(self.url,json=packet,headers=headers,timeout=12,allow_redirects=False)
            r.raise_for_status()
            if r.headers.get('Mcp-Session-Id'):
                self.session.headers['Mcp-Session-Id']=r.headers['Mcp-Session-Id']
            if notification:
                result={}
            else:
                if len(r.content)>131072:
                    raise ValueError('MCP 响应过大')
                value=r.json()
                if not isinstance(value,dict) or value.get('id')!=packet['id'] or 'error' in value:
                    raise ValueError('MCP RPC 响应无效')
                result=value['result']
                if not isinstance(result,dict):
                    raise ValueError('MCP result 须为对象')
            self.events.append({'request':packet,'response':result,'http_status':r.status_code})
            return result
        except (requests.RequestException,ValueError,KeyError) as error:
            raise DependencyError('MCP 服务不可用或返回无效响应') from error

    def discover(self):
        initialized=self.rpc('initialize',{'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'CampusClaw','version':'1.0'}})
        if initialized.get('protocolVersion')!='2025-03-26':
            raise DependencyError('MCP 协议版本不匹配')
        self.rpc('notifications/initialized',notification=True)
        tools=self.rpc('tools/list').get('tools',[])
        # Only the known read-only tool is executable; remote discovery is not authority.
        tools=[t for t in tools if t.get('name')=='course_deadline']
        return [{'type':'function','function':{'name':'mcp__'+t['name'],'description':t['description'],
            'parameters':t['inputSchema']}} for t in tools]

    def call(self,name,args):
        if name!='mcp__course_deadline' or args!={'course':'个人项目'}:
            raise ValueError('MCP 工具或参数不在白名单')
        return self.rpc('tools/call',{'name':'course_deadline','arguments':args})
