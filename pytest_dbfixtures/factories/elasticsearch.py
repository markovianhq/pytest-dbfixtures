# Copyright (C) 2013-2014 by Clearcode <http://clearcode.cc>
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

import urlparse
import pytest
from summon_process.executors import HTTPCoordinatedExecutor

from pytest_dbfixtures.utils import get_config


def elasticsearch_proc(host='127.0.0.1', port=9201, cluser_name=None):
    """
    Creates elasticsearch process fixture.

    :param str host: host that the instance listens on
    :param int port: port that the instance listens on
    :param str cluser_name: name of a cluser this node should work on.
        Used for autodiscovery. By default each node is in it's own cluser.
    """
    @pytest.fixture(scope='session')
    def elasticsearch_proc_fixture(request):
        """
        Elasticsearch process starting fixture.
        """
        config = get_config(request)

        pidfile = '/tmp/elasticsearch.{0}.pid'.format(port)
        home_path = '/tmp/elasticsearch_{0}'.format(port)
        logs_path = '/tmp/elasticsearch_{0}_logs'.format(port)
        work_path = '/tmp/elasticsearch_{0}_tmp'.format(port)
        cluster = cluser_name or 'dbfixtures.{0}'.format(port)

        command_exec = '''
            {deamon} -p {pidfile} -Des.http.port={port}
            -Des.path.home={home_path}  -Des.default.path.logs={logs_path}
            -Des.default.path.work={work_path}
            -Des.default.path.conf=/etc/elasticsearch
            -Des.cluster.name={cluster}
            '''.format(
            deamon=config.elasticsearch.deamon,
            pidfile=pidfile,
            port=port,
            home_path=home_path,
            logs_path=logs_path,
            work_path=work_path,
            cluster=cluster
        )

        elasticsearch_executor = HTTPCoordinatedExecutor(
            command_exec, 'http://{host}:{port}'.format(
                host=host,
                port=port
            ),
            timeout=10
        )

        elasticsearch_executor.start()

        def stop_elastic():
            if elasticsearch_executor.running():
                elasticsearch_executor.stop()

        request.addfinalizer(stop_elastic)
        return elasticsearch_executor

    return elasticsearch_proc_fixture
