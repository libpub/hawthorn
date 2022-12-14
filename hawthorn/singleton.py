#!/usr/bin/env python
# -*- coding: utf-8 -*-

# decorator of sigleton
def singleton(clsname):
    instances = {}
    def getinstance(*args,**kwargs):
        if clsname not in instances:
            instances[clsname] = clsname(*args,**kwargs)
        return instances[clsname]
    return getinstance
