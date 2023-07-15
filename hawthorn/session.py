#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import secrets
import json
import tornado.web
from .utilities import singleton
from .cacheproxy import CacheProxy

_all_user_session_info = {}

@singleton
class HandlerSessionDataManager():
    
    def __init__(self):
        self.session_data_map = {}
        self.cache_path = 'data/session-data.bin'
        if os.path.exists(self.cache_path):
            with open(self.cache_path, 'r+') as f:
                cont = f.read()
                data = json.loads(cont)
                for k, value in data.items():
                    self.session_data_map[k] = value
                f.close()

    def set_item(self, key: str, name: str, value: any):
        # CacheProxy().
        if key not in self.session_data_map:
            self.session_data_map[key] = {}
        self.session_data_map[key][name] = value
        self.save_to_cache()
    
    def get_item(self, key: str, name: str):
        data = self.session_data_map.get(key, None)
        if data:
            return data.get(name, None)
        return None
    
    def key_exists(self, key: str):
        return self.session_data_map.get(key, None)
    
    def delete(self, key: str):
        if key in self.session_data_map:
            del self.session_data_map[key]
        self.save_to_cache()

    def save_to_cache(self):
        data = json.dumps(self.session_data_map)
        if not os.path.exists(self.cache_path):
            path_name, _ = os.path.split(self.cache_path)
            if not os.path.exists(path_name):
                os.makedirs(path_name, 0o777)
        with open(self.cache_path, 'w+') as f:
            f.write(data)
            f.close()

_session_manager = HandlerSessionDataManager()

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
                if not _session_manager.key_exists(random_index_str):
                    self.random_index_str = self.__get_random_str()
            else:
                self.random_index_str = self.__get_random_str()
                self.handler.set_secure_cookie(SESSION_KEY, self.random_index_str)
        _session_manager.set_item(self.random_index_str, key, value)
        # if not self.random_index_str:
        #     random_index_str = self.handler.get_secure_cookie(SESSION_KEY, None)
        #     if random_index_str:
        #         if random_index_str not in _all_user_session_info:
        #             self.random_index_str = self.__get_random_str()
        #             _all_user_session_info[self.random_index_str] = {}
        #     else:
        #         self.random_index_str = self.__get_random_str()
        #         self.handler.set_secure_cookie(SESSION_KEY, self.random_index_str)
        #         _all_user_session_info[self.random_index_str] = {}
        # _all_user_session_info[self.random_index_str][key] = value
        self.handler.set_secure_cookie(SESSION_KEY, self.random_index_str)

    def __getitem__(self, key):
        self.random_index_str = self.handler.get_secure_cookie(SESSION_KEY, None)
        if self.random_index_str:
            self.random_index_str = str(self.random_index_str, encoding='utf-8')
            return _session_manager.get_item(self.random_index_str, key)
            # current_info = _all_user_session_info.get(self.random_index_str, None)
            # if current_info:
            #     return current_info.get(key, None)
        return None

    def delete(self):
        self.random_index_str = self.handler.get_secure_cookie(SESSION_KEY, None)
        if self.random_index_str:
            self.random_index_str = str(self.random_index_str, encoding='utf-8')
            _session_manager.delete(self.random_index_str)
            # if self.random_index_str in _all_user_session_info:
            #     del _all_user_session_info[self.random_index_str]
