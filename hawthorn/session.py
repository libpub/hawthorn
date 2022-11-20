#!/usr/bin/env python
# -*- coding: utf-8 -*-

import secrets
import tornado.web

_all_user_session_info = {}

SESSION_KEY = '__session__'

class TornadoSession(object):
    def __init__(self, handler: tornado.web.RequestHandler):
        self.handler = handler
        self.random_index_str = None

    def __get_random_str(self):
        return secrets.token_urlsafe()

    def __setitem__(self, key, value):
        if not self.random_index_str:
            random_index_str = self.handler.get_secure_cookie(SESSION_KEY, None)
            if random_index_str:
                if self.random_index_str not in _all_user_session_info:
                    self.random_index_str = self.__get_random_str()
                    _all_user_session_info[self.random_index_str] = {}
            else:
                self.random_index_str = self.__get_random_str()
                self.handler.set_secure_cookie(SESSION_KEY, self.random_index_str)
                _all_user_session_info[self.random_index_str] = {}
        _all_user_session_info[self.random_index_str][key] = value
        self.handler.set_secure_cookie(SESSION_KEY, self.random_index_str)

    def __getitem__(self, key):
        self.random_index_str = self.handler.get_secure_cookie(SESSION_KEY, None)
        if self.random_index_str:
            self.random_index_str = str(self.random_index_str, encoding='utf-8')
            current_info = _all_user_session_info.get(self.random_index_str, None)
            if current_info:
                return current_info.get(key, None)
        return None

    def delete(self):
        self.random_index_str = self.handler.get_secure_cookie(SESSION_KEY, None)
        if self.random_index_str:
            self.random_index_str = str(self.random_index_str, encoding='utf-8')
            if self.random_index_str in _all_user_session_info:
                del _all_user_session_info[self.random_index_str]
