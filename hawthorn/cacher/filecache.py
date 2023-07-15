#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import hashlib
import shelve
import pickle
import time
import tornado.gen

class FileCache:
    def __init__(self, cache_file):
        path_name, _ = os.path.split(cache_file)
        if not os.path.exists(path_name):
            os.makedirs(path_name, 0o777)
        self.cache = shelve.open(cache_file)

    def get_cache_key(self, key):
        hash_object = hashlib.md5(str(key).encode())
        return hash_object.hexdigest()

    @tornado.gen.coroutine
    def get(self, key):
        cache_key = self.get_cache_key(key)

        if cache_key in self.cache:
            data = self.cache[cache_key]
            if 'value' in data:
                if data.get('expiry', 0) >= time.time():
                    return data['value']
                else:
                    del self.cache[cache_key]

        return None

    @tornado.gen.coroutine
    def set(self, key, value, expire=None):
        cache_key = self.get_cache_key(key)

        if expire is not None:
            expiry_time = time.time() + expire
        else:
            expiry_time = None

        self.cache[cache_key] = {'value': value, 'expiry': expiry_time}

    @tornado.gen.coroutine
    def mget(self, keys):
        values = []

        for key in keys:
            values.append(self.get(key))

        return values

    @tornado.gen.coroutine
    def mset(self, mapping, expire=None):
        for key, value in mapping.items():
            self.set(key, value, expire)

    @tornado.gen.coroutine
    def hget(self, key, field):
        cache_key = self.get_cache_key(key)

        if cache_key in self.cache and isinstance(self.cache[cache_key], dict):
            data = self.cache[cache_key]
            if 'fields' in data:
                return data['fields'].get(field)

        return None

    @tornado.gen.coroutine
    def hset(self, key, field, value, expire=None):
        cache_key = self.get_cache_key(key)

        if cache_key not in self.cache:
            self.cache[cache_key] = {'fields': {}}

        self.cache[cache_key]['fields'][field] = value
        self.set(key, self.cache[cache_key], expire)

    @tornado.gen.coroutine
    def hmget(self, key, fields):
        cache_key = self.get_cache_key(key)

        if cache_key in self.cache and isinstance(self.cache[cache_key], dict):
            data = self.cache[cache_key]
            if 'fields' in data:
                values = []
                for field in fields:
                    values.append(data['fields'].get(field))
                return values

        return [None] * len(fields)

    @tornado.gen.coroutine
    def hmset(self, key, mapping, expire=None):
        cache_key = self.get_cache_key(key)

        if cache_key not in self.cache:
            self.cache[cache_key] = {'fields': {}}

        self.cache[cache_key]['fields'].update(mapping)
        self.set(key, self.cache[cache_key], expire)

    @tornado.gen.coroutine
    def delete(self, key):
        cache_key = self.get_cache_key(key)
        if cache_key in self.cache:
            del self.cache[cache_key]

    @tornado.gen.coroutine
    def smembers(self, key):
        cache_key = self.get_cache_key(key)

        if cache_key in self.cache:
            data = self.cache[cache_key]
            if 'members' in data:
                return data['members']

        return set()

    @tornado.gen.coroutine
    def sadd(self, key, *values):
        cache_key = self.get_cache_key(key)

        if cache_key not in self.cache:
            self.cache[cache_key] = {'members': set()}

        self.cache[cache_key]['members'].update(values)
        
    @tornado.gen.coroutine
    def hscan(self, key, cursor=0, count=None):
        cache_key = self.get_cache_key(key)

        if cache_key in self.cache:
            data = self.cache[cache_key]
            if 'fields' in data:
                fields = list(data['fields'].keys())
                cursor = int(cursor)
                if count is None:
                    count = len(fields)
                else:
                    count = int(count)

                fields_slice = fields[cursor : cursor + count]
                next_cursor = cursor + count if cursor + count < len(fields) else 0

                result = []
                for field in fields_slice:
                    result.append((field, data['fields'][field]))

                return next_cursor, result

        return 0, []

    @tornado.gen.coroutine
    def hgetall(self, key):
        cache_key = self.get_cache_key(key)

        if cache_key in self.cache and isinstance(self.cache[cache_key], dict):
            data = self.cache[cache_key]
            if 'fields' in data:
                return data['fields']

        return {}

    @tornado.gen.coroutine
    def zrange(self, key, start, stop, withscores=False):
        cache_key = self.get_cache_key(key)

        if cache_key in self.cache:
            data = self.cache[cache_key]
            if 'sorted_set' in data:
                sorted_set = data['sorted_set']

                if isinstance(sorted_set, dict):
                    sorted_set = sorted(sorted_set.items(), key=lambda x: x[1])

                if withscores:
                    return sorted_set[start : stop + 1]
                else:
                    return [item[0] for item in sorted_set[start : stop + 1]]

        return []

    @tornado.gen.coroutine
    def sismember(self, key, value):
        cache_key = self.get_cache_key(key)

        if cache_key in self.cache:
            data = self.cache[cache_key]
            if 'members' in data:
                return value in data['members']

        return False
        
    def close(self):
        self.cache.close()


