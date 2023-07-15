#!/usr/bin/env python
# -*- coding: utf-8 -*-

import redis
import logging
import datetime
import tornado.gen
import aredis

from .modelutils import model_columns, format_mongo_value, DEFAULT_SKIP_FIELDS
from .dbproxy import DbProxy
from .cacheproxy import CacheProxy

LOG = logging.getLogger('components.db2cachehelper')

@tornado.gen.coroutine
def load_mongo_data_to_cache(model, keyPrefix, pk, filters=None, excachecb=None, clearcache=True):
    cacheproxy = CacheProxy()
    check_uniques = {}
    @tornado.gen.coroutine
    def _load_cache_pk(item):
        cache_key = keyPrefix + cacheproxy.get_index_key_value(item, pk)
        if cache_key in check_uniques:
            LOG.warning('loadToCache by key:%s that already exists.', cache_key)
        check_uniques[cache_key] = 1
        yield cacheproxy.set_object(cache_key, item)
        if callable(excachecb):
            yield excachecb(item, cacheproxy.async_redis_conn)

    if clearcache:
        yield cacheproxy.clear_by_key_prefix(keyPrefix)
    yield load_data_from_mongodb(model, _load_cache_pk, filters=filters)

@tornado.gen.coroutine
def load_mongo_data_to_cache_indexed_to_many(model, keyPrefix, indexKey, pk, filters=None, orderby=None, clearcache=True):
    cacheproxy = CacheProxy()
    @tornado.gen.coroutine
    def _load_cache_index(item):
        yield cacheproxy.add_to_cache_indexed_to_many(item, keyPrefix, indexKey, pk)
    if clearcache:
        yield cacheproxy.clear_by_key_prefix(keyPrefix)
    yield load_data_from_mongodb(model, _load_cache_index, filters=filters, orderby=orderby)

@tornado.gen.coroutine
def load_data_from_mongodb(model, cb, filters=None, orderby=None):
    dbproxy = DbProxy()
    limit = 5000
    offset = 0
    nrows = limit
    modelName = str(model.__name__)
    LOG.info("loading %s from db begining", modelName)
    qfilters = []
    kwfilters = {}
    curId = None
    if isinstance(filters, tuple):
        for f in filters:
            if isinstance(f, dict):
                for k,v in f.items():
                    kwfilters[k] = v
            elif isinstance(f, list):
                for v in f:
                    qfilters.append(v)
    elif isinstance(filters, dict):
        kwfilters = filters
    elif isinstance(filters, list):
        qfilters = filters
    while nrows >= limit:
        if curId:
            kwfilters['id__gt'] = curId
        rows = yield dbproxy.query_all_mongo(model, (qfilters, kwfilters), limit)
        nrows = 0
        for row in rows:
            nrows += 1
            curId = row.get('id')
            item = {}
            for k in row:
                if k in DEFAULT_SKIP_FIELDS:
                    continue
                item[k] = format_mongo_value(row.get(k))
            if tornado.gen.is_coroutine_function(cb):
                yield cb(item)
            else:
                cb(item)
        offset += nrows
        LOG.info("loading %s from db offset:%d rows:%d", modelName, offset, nrows)
    
    LOG.info("loading %s from db finished", modelName)

