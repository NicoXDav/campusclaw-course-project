from contextlib import contextmanager
from threading import Thread
import requests
from werkzeug.serving import make_server
from app.platform_tools import MCPClient
from app.providers import DependencyError
import pytest


def test_real_http_mcp_lifecycle_and_tool_result():
    from app.mcp_server import create_mcp_app
    server=make_server('127.0.0.1',0,create_mcp_app())
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        client=MCPClient(f'http://127.0.0.1:{server.server_port}/mcp')
        tools=client.discover()
        assert tools[0]['function']['name']=='mcp__course_deadline'
        result=client.call('mcp__course_deadline',{'course':'个人项目'})
        assert '2026-10-28' in result['content'][0]['text']
        assert [e['request']['method'] for e in client.events]==['initialize','notifications/initialized','tools/list','tools/call']
        bad=requests.post(client.url,json={'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'shell','arguments':{}}})
        assert 'error' in bad.json()
        assert requests.post(client.url,headers={'Origin':'https://untrusted.example'},json={'jsonrpc':'2.0','id':1,'method':'tools/list'}).status_code==403
    finally:
        server.shutdown();thread.join()


def test_malformed_mcp_response_is_dependency_error(monkeypatch):
    class Response:
        headers={};content=b'[]';status_code=200
        def raise_for_status(self):pass
        def json(self):return []
    monkeypatch.setattr('app.platform_tools.requests.Session.post',lambda *args,**kwargs:Response())
    with pytest.raises(DependencyError):
        MCPClient('http://127.0.0.1:8090/mcp').discover()
