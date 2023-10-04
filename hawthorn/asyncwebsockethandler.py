#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from typing import Any
import struct
import time
import json
import asyncio
from wtforms import Form
import tornado.gen
import tornado.web
from tornado import httputil
import tornado.websocket
from hawthorn.utilities import Constant, singleton
from hawthorn.asynchttphandler import async_tornado_handler
from lycium_rest.formvalidation import validate_form
from lycium_rest.restfulwrapper import SESSION_UID_KEY
from lycium_rest.valueobjects.responseobject import GeneralResponseObject
from lycium_rest.valueobjects.resultcodes import RESULT_CODE

LOG = logging.getLogger('hawthorn.asyncwebsockethandler')

@singleton
class WebsocketBizHandlers():
    """
    """
    def __init__(self):
        self.handlers = {}

_websocket_biz_handlers = WebsocketBizHandlers()

def websocket_handler(biz_code: str, **options):
    """Register a websocket handler by a callable handler
    
    : biz_code string (required): code match rule for handler
    
    Wrappered decorator function: callback handler

        Args:
            data (dict): request payload data
            handler (AsyncWebSocketHandler): base websocket handler

        Returns:
            bool, str: success or not, response data
    
    """
    def decorator(f):
        """callback handler

        Args:
            data (dict): request payload data
            handler (AsyncWebSocketHandler): base websocket handler

        Returns:
            bool, str: success or not, response data
        """
        # endpoint = options.pop('endpoint', None)
        # if not endpoint:
        #     endpoint = f.__name__
        ac = options.pop('ac', [])

        _websocket_biz_handlers.handlers[biz_code] = f
        return f
    return decorator

class _WSCommands(Constant):
    PING = 100
    SERVER_TIME = 101
    LOGIN = 102
    LOGOUT = 103
    BIZ = 200

WSCMD = _WSCommands()

class WSPackage():
    def __init__(self, buf: str|bytes):
        buf_len = len(buf)
        if buf_len >= 20:
            pieces = struct.unpack('>LHBBLLL', buf[0:20])
        self.len = int(pieces[0])
        self.cmd = int(pieces[1])
        self.agent = int(pieces[2])
        self.flag = int(pieces[3])
        self.seq = int(pieces[4])
        self.src = int(pieces[5])
        self.client = int(pieces[6])
        rest_buf = buf[20:]
        self.message = rest_buf
    
# Websocket Clients manager mapped by uid
@singleton
class WSClientManager():
    
    def __init__(self):
        # Websocket Clients mapped by uid
        self.clients = {}

    def get(self, uid: int|str):
        return self.clients.get(uid, None)

    def add(self, uid: int|str, ws_session: tornado.websocket.WebSocketHandler):
        self.clients[uid] = ws_session

    def remove(self, uid: int|str):
        if uid in self.clients:
            del self.clients[uid]
    
class AsyncWebSocketHandler(tornado.websocket.WebSocketHandler):
    
    biz_code_field_name = 'bizCode'
    payload_field_name = 'payload'
    # def __init__(self, application: Application, request: HTTPServerRequest, **kwargs: Any) -> None:
    #     super().__init__(application, request, **kwargs)
    
    def verify_token(self, token):
        """Overwirte this method to implement token parsing logic.
        Returns user id when token verified successfully
        """
        return 0
    
    # 有新的连接时open()函数将会被调用,将客户端的连接统一放到clients
    def open(self, *args, **kwargs):
        self.is_login = False
        self.id = 0
        token = self.get_argument('token')
        if token:
            if not self.do_authorize({'data': {'token': token}}):
                self.close()
                return
       
        # self.stream.set_nodelay(True)
        LOG.info("websocket connection opened...")

    # 客户收到消息将被调用
    def on_message(self, message):
        ok = False
        pkg = WSPackage(message)
        LOG.debug("client %s received a message: %s" % (self.id, str(pkg.message)))
        if pkg.cmd == WSCMD.LOGIN:
            ok, params = self.parse_inputs(pkg.message)
            if ok:
                ok = self.do_authorize(params)
        elif pkg.cmd == WSCMD.LOGOUT:
            self.close()
            ok = True
        elif pkg.cmd == WSCMD.PING:
            self.write_message('pong')
            ok = True
        elif pkg.cmd == WSCMD.SERVER_TIME:
            resp = {
                'code': 0,
                'ts': time.time()
            }
            self.write_message(json.dumps(resp))
            ok = True
        else:
            ok, params = self.parse_inputs(pkg.message)
            if ok:
                ok, resp = self.do_biz(params)
                if ok:
                    self.write_message(resp)

        if not ok:
            self.close()

    # 关闭连接时被调用
    def on_close(self):
        self.is_login = False
        WSClientManager().remove(self.id)
        LOG.warning("client %s is closed" % self.id)

    def check_origin(self, origin):
        return True

    def parse_inputs(self, message: bytes|str):
        try:
            params = json.loads(message)
        except Exception as e:
            LOG.error('parsing client input failed with invalid input formation: %s', str(e))
            return False, {}
        if not isinstance(params, dict):
            LOG.error('parsing client input failed with invalid input formation: the input data is not dict type')
            return False, {}
        return True, params
    
    def do_authorize(self, params: dict):
        data = params.get('data', {})
        token = str(data.get('token', None))
        if not token:
            LOG.warning('client do login failed with empty token')
            return False
        uid = self.verify_token(token)
        if not uid:
            LOG.warning('client do login with invalid token:%s connected, now break it', token)
            return False
        self.token = token
        self.id = int(uid)
        self.is_login = True
        WSClientManager().add(self.id, self)
        if params.get(self.biz_code_field_name, None):
            resp_msg = {
                self.biz_code_field_name: params.get(self.biz_code_field_name, ''),
                'requestId': params.get('requestId', ''),
                'data': {
                    'id': self.id,
                }
            }
            self.write_message(json.dumps(resp_msg))
        return True
        
    def do_biz(self, params: dict):
        biz_code = params.get(self.biz_code_field_name, '')
        data = params.get(self.payload_field_name, {})
        
        callback = _websocket_biz_handlers.handlers.get(biz_code, None)
        if callable(callback):
            b, msg = asyncio.ensure_future(self._call(callback, data, handler=self))
            return b, msg
        
        return False, ''
    
    async def _call(self, callable: callable, **kwargs):
        if tornado.gen.is_coroutine_function(callable) or asyncio.iscoroutinefunction(callable):
            return await callable(**kwargs)
        else:
            return callable(**kwargs)
        