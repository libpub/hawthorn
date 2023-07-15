#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import datetime
import tornado.gen
import aredis

from .supports import singleton
from .modelutils import model_columns, DEFAULT_SKIP_FIELDS
from .cacher.filecache import FileCache

LOG = logging.getLogger('components.cacheproxy')

@singleton
class CacheProxy(object):
    """
    Cacher agent component
    """

    def __init__(self):
        self.cache_inst = None
    
    def configure(self, conf: dict):
        if conf.get('type', None) == 'redis':
            self.configure_redis(conf)
        elif conf.get('type', None) == 'file':
            self.configure_filecache(conf.get('path', 'data/file-caching.db'))
        else:
            LOG.error('configure cacheproxy with configure:%s failed with unknown cache type', str(conf))
    
    def configure_redis(self, redis_conf: dict):
        self.cache_inst = aredis.StrictRedis(host=redis_conf.get('host', 'localhost'), port=redis_conf.get('port', 6379), 
            db=redis_conf.get('db', 0), password=redis_conf.get('password', None), retry_on_timeout=True)
        return True
    
    def configure_filecache(self, cache_path: str):
        self.cache_inst = FileCache(cache_path)

    def prepare(self):
        if self.cache_inst == None:
            self.configure_filecache('data/file-caching.db')

    @tornado.gen.coroutine
    def get_object(self, key, keys):
        self.prepare()
        res = yield self.cache_inst.hmget(key, keys)
        if not res:
            return False
        result = {}
        is_all_none = True
        i = 0
        for k in keys:
            v = res[i].decode() if isinstance(res[i], bytes) else res[i]
            result[k] = v
            i += 1
            if is_all_none and v is not None:
                is_all_none = False
        if is_all_none:
            result = False
        return result
    
    @tornado.gen.coroutine
    def get_objects(self, key, keys):
        self.prepare()
        results = []
        idxes = yield self.get_sets_values(key)
        for idx in idxes:
            row = yield self.get_object(key+':'+idx, keys)
            if row is not False:
                results.append(row)
        return results

    @tornado.gen.coroutine
    def set_object(self, key, mapping, expire=None):
        if not mapping:
            return False
        for k,v in mapping.items():
            if v is None:
                mapping[k] = ''
        yield self.cache_inst.hmset(key, mapping, expire=expire)
        return True

    @tornado.gen.coroutine
    def get_sets_values(self, key):
        results = []
        vals = yield self.cache_inst.smembers(key)
        if not vals:
            return results
        for val in vals:
            val = val.decode() if isinstance(val, bytes) else str(val)
            results.append(val)
        return results

    @tornado.gen.coroutine
    def add_sets_values(self, key, value):
        yield self.cache_inst.sadd(key, value)
        
    @tornado.gen.coroutine
    def get_sets_values_extend(self, key, keys):
        vals = yield self.get_sets_values(key)
        return self.parse_imploded_values(vals, keys)

    def parse_imploded_values(self, rows, keys):
        results = []
        if not rows:
            return results
        l = len(keys)
        for val in rows:
            one = {k:'' for k in keys}
            i = 0
            eles = val.split('-')
            l2 = len(eles)
            for i in range(l):
                if i < l2:
                    one[keys[i]] = eles[i]
            # in case that if last field is text that contains '-'
            if l > 0 and l2 > l:
                for j in range(l2-l):
                    one[keys[l-1]] += '-' + eles[l+j]
            results.append(one)
        return results
        
    @tornado.gen.coroutine
    def get_sorted_sets_values(self, key):
        results = []
        vals = yield self.zrange(key, 0, -1, withscores=True)
        if not vals:
            return results
        for ele in vals:
            val = ele[0]
            val = val.decode() if isinstance(val, bytes) else val
            results.append(val)
        return results
    
    @tornado.gen.coroutine
    def get_sorted_sets_value_extend(self, key, keys):
        vals = yield self.get_sorted_sets_values(key)
        return self.parse_imploded_values(vals, keys)

    @tornado.gen.coroutine
    def get_cache_value(self, key):
        val = yield self.cache_inst.get(key)
        return val

    @tornado.gen.coroutine
    def scan_hash_keys(self, hash_key, key_match, count=1000, cursor=0):
        res = yield self.cache_inst.hscan(hash_key, cursor, match=key_match, count=count)
        keys = []
        next_cursor = 0
        if res:
            next_cursor = res[0]
            for k in res[1]:
                keys.append(k.decode() if isinstance(k, bytes) else str(k))
        return keys, next_cursor
    
    @tornado.gen.coroutine
    def find_hash_keys(self, hash_key, key_match, match_keys = {}):
        keys = []
        if not hash_key or not key_match or not match_keys:
            return keys
        next_cursor = -1
        while next_cursor != 0:
            if next_cursor == -1:
                next_cursor = 0
            scanedKeys, next_cursor = yield self.scan_hash_keys(hash_key, key_match, cursor=next_cursor)
            for k in scanedKeys:
                if k in match_keys:
                    keys.append(k)
        return keys

    @tornado.gen.coroutine
    def get_all_hash_keys(self, hash_key_prefix, match_keys = {}):
        res = yield self.cache_inst.hgetall(hash_key_prefix)
        result = []
        for row in res:
            a = row
        return result
        
    @tornado.gen.coroutine
    def clear_by_key_prefix(self, key_prefix):
        keys = yield self.cache_inst.keys(key_prefix+'*')
        del_keys = [[]]
        i = 0
        for k in keys:
            del_keys[i].append(k.decode() if isinstance(k, bytes) else str(k))
            if len(del_keys[i]) > 50:
                i += 1
                del_keys.append([])

            if i > 10:
                yield [self.cache_inst.delete(*dkeys) for dkeys in del_keys]
                del_keys = [[]]
                i = 0
        
        if del_keys[0]:
            yield [self.cache_inst.delete(*dkeys) for dkeys in del_keys]

    @tornado.gen.coroutine
    def incr(self, key, expire = None):
        yield self.cache_inst.incr(key)
        if expire:
            yield self.cache_inst.expire(key, expire)

    @tornado.gen.coroutine
    def set(self, key, value, expire = None, px=None, nx=False, xx=False):
        """
        Set the value at key ``name`` to ``value``

        ``expire`` sets an expire flag on key ``name`` for ``expire`` seconds.

        ``px`` sets an expire flag on key ``name`` for ``px`` milliseconds.

        ``nx`` if set to True, set the value at key ``name`` to ``value`` only
            if it does not exist.

        ``xx`` if set to True, set the value at key ``name`` to ``value`` only
            if it already exists.
        """
        yield self.cache_inst.set(key, value, ex=expire, px=px, nx=nx, xx=xx)

    @tornado.gen.coroutine
    def get(self, key):
        val = yield self.cache_inst.get(key)
        return val

    @tornado.gen.coroutine
    def delete(self, key):
        val = yield self.cache_inst.delete(key)
        return val

    @tornado.gen.coroutine
    def zrange(self, name, start, end, desc=False, withscores=False,
               score_cast_func=float):
        """
        Return a range of values from sorted set ``name`` between
        ``start`` and ``end`` sorted in ascending order.

        ``start`` and ``end`` can be negative, indicating the end of the range.

        ``desc`` a boolean indicating whether to sort the results descendingly

        ``withscores`` indicates to return the scores along with the values.
        The return type is a list of (value, score) pairs

        ``score_cast_func`` a callable used to cast the score return value
        """
        val = yield self.cache_inst.zrange(name, start, end, desc=desc, withscores=withscores, score_cast_func=score_cast_func)
        return val

    @tornado.gen.coroutine
    def is_exists_in_sets(self, key, value):
        val = yield self.cache_inst.sismember(key, value)
        return val

    @tornado.gen.coroutine
    def add_to_cache_indexed_to_many(self, item, key_prefix, index_key, pk):
        if not isinstance(item, dict):
            item2 = item
            item = {}
            columns,_ = model_columns(item2)
            for k in columns:
                if k not in DEFAULT_SKIP_FIELDS:
                    item[k] = getattr(item2, k)
        pk_value = self.get_index_key_value(item, pk)
        idx_value = self.get_index_key_value(item, index_key)
        cache_key = key_prefix + idx_value
        yield self.cache_inst.sadd(cache_key, pk_value)
        cache_key += ':' + pk_value
        yield self.set_object(cache_key, item)

    @tornado.gen.coroutine
    def del_from_cache_indexed_to_many(self, item, key_prefix, index_key, pk):
        pk_value = self.get_index_key_value(item, pk)
        idx_value = self.get_index_key_value(item, index_key)
        cache_key = key_prefix + idx_value
        yield self.cache_inst.srem(cache_key, pk_value)
        cache_key += ':' + pk_value
        yield self.cache_inst.delete(cache_key)

    def get_index_key_value(self, item, index_key):
        idx_value = ''
        if isinstance(index_key, list):
            vals = []
            for k in index_key:
                if isinstance(item, dict):
                    vals.append(str(item[k]) if item[k] is not None else '')
                else:
                    vals.append(str(getattr(item, k, '')))
            idx_value = ':'.join(vals)
        else:
            if isinstance(item, dict):
                idx_value = str(item[index_key] if item[index_key] is not None else '')
            else:
                idx_value = str(getattr(item, index_key, ''))
        return idx_value
