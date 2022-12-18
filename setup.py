#!/usr/bin/python
#-*- coding:utf-8 -*-

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="hawthorn",
    version="0.0.2",
    author="kevinyjn",
    author_email="kevinyjn@gmail.com",
    description="common python programing encapsulation library",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/libpub/hawthorn",
    packages=setuptools.find_packages(exclude=[".tests", ".tests.", "tests.*", "tests"]),
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=[
        "pycrypto",
        "blinker",
        "pika",
        "redis",
        "gunicorn",
        "mongoengine",
        "elasticsearch==7.12.0",
        "sqlalchemy==1.4.25",
        "sshtunnel",
        "Cython",
        "IPy",
        "requests",
        "tornado",
        "zeep[async]",
        "pycurl",
        "motor",
        "aredis",
        "pyopenssl",
        "rsa",
        "cx_Oracle",
        "asyncpg",
        "aiomysql",
        "aiosqlite",
        "pymssql",
        "protobuf==3.14.0",
        "PyJWT",
        "python-i18n[YAML]"
    ]
)
