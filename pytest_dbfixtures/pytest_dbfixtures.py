# Copyright (C) 2013 by Clearcode <http://clearcode.cc>
# and associates (see AUTHORS).

# This file is part of pytest-dbfixtures.

# pytest-dbfixtures is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# pytest-dbfixtures is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public License
# along with pytest-dbfixtures.  If not, see <http://www.gnu.org/licenses/>.

import os
import shutil
import importlib

import pytest
from path import path
from pymlconf import ConfigManager
from summon_process.executors import TCPCoordinatedExecutor


ROOT_DIR = path(__file__).parent.parent.abspath()


def get_config(request):
    config_name = request.config.getvalue('db_conf')
    return ConfigManager(files=[config_name])


def try_import(module, request):
    try:
        i = importlib.import_module(module)
    except ImportError:
        raise ImportError('Please install {0} package.\n'
                          'pip install -U {0}'.format(module))
    else:

        return i, get_config(request)


def pytest_addoption(parser):
    parser.addoption(
        '--dbfixtures-config',
        action='store',
        default=ROOT_DIR / 'pytest_dbfixtures' / 'dbfixtures.conf',
        metavar='path',
        dest='db_conf',
    )

    parser.addoption(
        '--mongo-config',
        action='store',
        default=ROOT_DIR / 'pytest_dbfixtures' / 'mongo.conf',
        metavar='path',
        dest='mongo_conf',
    )

    parser.addoption(
        '--redis-config',
        action='store',
        default=ROOT_DIR / 'pytest_dbfixtures' / 'redis.conf',
        metavar='path',
        dest='redis_conf',
    )

    parser.addoption(
        '--rabbit-config',
        action='store',
        default=ROOT_DIR / 'pytest_dbfixtures' / 'rabbit.conf',
        metavar='path',
        dest='rabbit_conf',
    )


@pytest.fixture(scope='session')
def redis_proc(request):
    config = get_config(request)
    redis_conf = request.config.getvalue('redis_conf')

    redis_executor = TCPCoordinatedExecutor(
        '{redis_exec} {params} {config}'.format(
            redis_exec=config.redis.redis_exec,
            params=config.redis.params,
            config=redis_conf),
        host=config.redis.host,
        port=config.redis.port,
    )
    redis_executor.start()

    request.addfinalizer(redis_executor.stop)
    return redis_executor


@pytest.fixture
def redisdb(request, redis_proc):
    redis, config = try_import('redis', request)

    redis_client = redis.Redis(
        config.redis.host,
        config.redis.port,
        config.redis.db,
    )
    request.addfinalizer(redis_client.flushall)
    return redis_client


@pytest.fixture(scope='session')
def mongo_proc(request):
    config = get_config(request)
    mongo_conf = request.config.getvalue('mongo_conf')

    mongo_executor = TCPCoordinatedExecutor(
        '{mongo_exec} {params} {config}'.format(
            mongo_exec=config.mongo.mongo_exec,
            params=config.mongo.params,
            config=mongo_conf),
        host=config.mongo.host,
        port=config.mongo.port,
    )
    mongo_executor.start()

    def stop():
        mongo_executor.stop()
    request.addfinalizer(stop)
    return mongo_executor


@pytest.fixture
def mongodb(request, mongo_proc):
    pymongo, config = try_import('pymongo', request)

    mongo_conn = pymongo.Connection(
        config.mongo.host,
        config.mongo.port
    )

    mongodb = mongo_conn[config.mongo.db]

    def drop():
        for collection_name in mongodb.collection_names():
            if collection_name != 'system.indexes':
                mongodb[collection_name].drop()

    request.addfinalizer(drop)
    drop()
    return mongodb


@pytest.fixture
def rabbitmq(request):
    pika, config = try_import('pika', request)
    
    rabbit_conf = request.config.getvalue('rabbit_conf')
    for line in open(rabbit_conf):
        name, value = line[:-1].split('=')
        os.environ[name] = value

    rabbit_executor = TCPCoordinatedExecutor(
        '{rabbit_exec}'.format(
            rabbit_exec=config.rabbit.rabbit_server,
        ),
        host=config.rabbit.host,
        port=config.rabbit.port,
    )
    rabbit_executor.start()

    def stop_and_reset():
        rabbit_executor.stop()
        shutil.rmtree(os.environ['RABBITMQ_MNESIA_BASE'])
    request.addfinalizer(stop_and_reset)

    rabbit_params = pika.connection.ConnectionParameters(
        host=config.rabbit.host,
        port=config.rabbit.port,
    )
    rabbit_connection = pika.BlockingConnection(rabbit_params)
    return rabbit_connection
