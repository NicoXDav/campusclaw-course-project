"""Read-only course MCP server, JSON-only stateless Streamable HTTP transport."""
import json
from urllib.parse import urlparse
from flask import Flask, request, jsonify


def create_mcp_app():
    app=Flask('campusclaw-mcp')
    app.config['MAX_CONTENT_LENGTH']=16384

    @app.post('/mcp')
    def mcp():
        if request.headers.get('Origin') and urlparse(request.headers['Origin']).netloc!=request.host:
            return jsonify(error='Origin rejected'),403
        p=request.get_json(silent=True)
        if not isinstance(p,dict) or p.get('jsonrpc')!='2.0':
            return jsonify(jsonrpc='2.0',id=None,error={'code':-32600,'message':'Invalid Request'}),400
        method=p.get('method');params=p.get('params',{})
        if method=='notifications/initialized':
            return '',202
        error=None
        if method=='initialize':
            result={'protocolVersion':'2025-03-26','capabilities':{'tools':{'listChanged':False}},
                'serverInfo':{'name':'CampusClaw Course Tools','version':'1.0'}}
        elif method=='tools/list':
            result={'tools':[{'name':'course_deadline','description':'查询个人项目阶段性验收的截止日期与交付物',
                'inputSchema':{'type':'object','properties':{'course':{'type':'string','enum':['个人项目']}},'required':['course'],'additionalProperties':False}}]}
        elif method=='tools/call' and isinstance(params,dict) and params.get('name')=='course_deadline' and params.get('arguments')=={'course':'个人项目'}:
            result={'content':[{'type':'text','text':json.dumps({'course':'个人项目','deadline':'2026-10-28 00:00 Asia/Shanghai',
                'deliverables':['Git 仓库地址','项目介绍','五项验证','PDF 报告'],'source':'教师发布的中期验收要求'},ensure_ascii=False)}],'isError':False}
        else:
            error={'code':-32601,'message':'Unknown method or disallowed tool arguments'}
        if error:
            return jsonify(jsonrpc='2.0',id=p.get('id'),error=error)
        return jsonify(jsonrpc='2.0',id=p.get('id'),result=result)
    return app


if __name__=='__main__':
    create_mcp_app().run(host='0.0.0.0',port=8090)
