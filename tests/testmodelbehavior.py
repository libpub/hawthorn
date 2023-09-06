#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys
import logging
from sqlalchemy import Column, Integer, String, ForeignKey
from hawthorn.dbproxy import DbProxy
from hawthorn.modelutils import ModelBase, meta_data
from hawthorn.modelutils.behaviors import ModifyingBehevior
import unittest
import inspect

class CONF:
    rdbms = {
        'default': {
            'connector': "sqlite",
            'driver': "sqlite",
            'host': "./unittest.db",
            'port': 0,
            'user': "changeit",
            'pwd': "changeit",
            'db': "unittest",
        }
    }
    
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

def get_current_value(*args, **kwargs):
    fs = sys._current_frames()
    st = inspect.stack()
    f0 = sys._getframe(0)
    f1 = sys._getframe(1)
    f2 = sys._getframe(2)
    f3 = sys._getframe(3)
    fi1 = inspect.getargvalues(st[1].frame)
    fi2 = inspect.getargvalues(st[2].frame)
    fi3 = inspect.getargvalues(st[3].frame)
    i = 0
    tr = inspect.trace(2)
    # for stack in st:
    #     fi = inspect.getargvalues(stack.frame)
    #     for k in fi.locals.keys():
    #         print('    ----> ', k, ':', fi.locals[k])
    #     print('====================================================')
    #     i = i + 1
    f_locals = sys._getframe(1).f_locals
    ctx = f_locals.get('ctx', None)
    if ctx is not None:
        if hasattr(ctx, 'get_session_uid'):
            uid_getter = getattr(ctx, 'get_session_uid', '')
            uid = uid_getter()
            print('=======================> uid:', uid)
            return uid
    # col = f2.f_locals.get('column', None)
    # if col is not None:
    #     model = col.entity_namespace
    #     if hasattr(model, 'get_session_uid'):
    #         uid_getter = getattr(model, 'get_session_uid')
    #         uid = uid_getter()
    #         print('current_uid:', uid)
    #         return uid
    # print('-------------------')
    return ''

class _OrganizationTable(ModelBase):
    __tablename__ = 'sys_organization'
    
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    code = Column('code', String(64), index=True)
    name = Column('name', String(64), index=True)
    parent_id = Column('parent_id', ForeignKey('sys_organization.id'), index=True, default=0)
    auto_value = Column('auto_value', Integer, default=get_current_value, onupdate=get_current_value)

class Organization(_OrganizationTable, ModifyingBehevior):
    """
    组织机构表
    """
    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)

APP_NAME = 'hawthorn.unittest'
LOG = logging.getLogger(APP_NAME)

async def create_tables():
    # ensure table were created
    dbinstance = DbProxy().get_model_dbinstance(Organization)
    async with dbinstance.engine.begin() as conn:
        await conn.run_sync(meta_data.create_all)
        LOG.info('ensure all table meta data were created')
        
class TestModelRESTful(unittest.IsolatedAsyncioTestCase):
    
    async def asyncSetUp(self):
        print("Application loading...")
        if CONF.rdbms:
            if os.path.exists(CONF.rdbms['default'].get('host')):
                os.remove(CONF.rdbms['default'].get('host'))
            DbProxy().setup_rdbms(CONF.rdbms)
        print("Application initializing...")
        await create_tables()
        print("Application running...")
        self.addAsyncCleanup(self.do_cleanup)
        
    async def test_model_beheavior(self):
        o = Organization()
        o.set_session_uid(APP_NAME)
        o.code = '640101'
        o.name = 'Testing Organization'
        o.parent_id = 0
        await DbProxy().insert_item(o, auto_flush=True)
        
        o = await DbProxy().find_item(Organization, {Organization.code=='640101'})
        print(f'Organization data code:{o.code} name:{o.name} created_at:{o.created_at} updated_at:{o.updated_at} created_by:{o.created_by} updated_by:{o.updated_by}')
        self.assertTrue(o.created_at > 0, 'auto set created_at behavior does not make sense')
        self.assertTrue(o.updated_at > 0, 'auto set updated_at behavior does not make sense')
        self.assertTrue(o.created_by != '', 'auto set created_by behavior does not make sense')
        self.assertTrue(o.updated_by != '', 'auto set updated_by behavior does not make sense')
        last_updated_at = o.updated_at
    
        o.set_session_uid('testing.modifier')
        o.name = 'Testing Organization 2'
        await DbProxy().update_item(o)
        o = await DbProxy().find_item(Organization, {Organization.code=='640101'})
        print(f'Organization data code:{o.code} name:{o.name} created_at:{o.created_at} updated_at:{o.updated_at} created_by:{o.created_by} updated_by:{o.updated_by}')
        self.assertNotEqual(o.updated_at, last_updated_at, 'auto update updated_at behavior does not make sense')
        self.assertEqual(o.updated_by, 'testing.modifier', 'auto update updated_by behavior does not make sense')
    
    async def do_cleanup(self):
        print("clean testing db ...")
        os.remove(CONF.rdbms['default'].get('host'))
        print("testing finished.")
        
if __name__ == '__main__':
    unittest.main()
