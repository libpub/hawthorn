#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
from sqlalchemy import Column, Integer, SmallInteger, String, BigInteger, func
# from sqlalchemy.ext.declarative import declarative_base
import flask
from hawthorn.utilities import get_current_timestamp_millis

def get_current_uid(*args, **kwargs):
    # uid = str(flask.session.get('uid', ''))
    uid = ''
    if flask.session:
        uid = str(flask.session.get('uid', ''))
    return uid

class AppBehevior(object):
    """
    接入方相关字段定义
    """
    app_id = Column('app_id', String(50), index=True, nullable=False)

class ModifyingBehevior(object):
    """
    修改相关字段定义
    """
    def __init__(self, session_uid=''):
        self.__session_uid = session_uid
        self.created_by.onupdate = self.get_session_uid
        self.created_by.default = self.get_session_uid
        self.updated_by.onupdate = self.get_session_uid
        self.updated_by.default = self.get_session_uid

    obsoleted = Column('obsoleted', SmallInteger, default=0, comment='废弃标志 0:正常 1:废弃')
    created_at = Column('created_at', BigInteger, default=get_current_timestamp_millis, comment='创建时间戳（毫秒）')
    updated_at = Column('updated_at', BigInteger, default=get_current_timestamp_millis, onupdate=get_current_timestamp_millis, comment='更新时间戳（毫秒）')
    created_by = Column('created_by', String(50), default=get_current_uid, comment='创建者用户ID')
    updated_by = Column('updated_by', String(50), default=get_current_uid, onupdate=get_current_uid, comment='更新者用户ID')

    def get_session_uid(self):
        if self.__session_uid:
            return self.__session_uid
        return get_current_uid()
    
    def set_session_uid(self, session_uid: str):
        self.__session_uid = str(session_uid)
        