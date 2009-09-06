# Copyright 2009 Mike Wakerly <opensource@hoho.com>
#
# This file is part of the Pykeg package of the Kegbot project.
# For more information on Pykeg or Kegbot, see http://kegbot.org/
#
# Pykeg is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# Pykeg is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Pykeg.  If not, see <http://www.gnu.org/licenses/>.

"""Kegnet API client library."""


import httplib
import logging
import socket
import urllib

from pykeg.core.net import kegnet_message
from pykeg.external.gflags import gflags

FLAGS = gflags.FLAGS

gflags.DEFINE_string('kb_core_hostname', 'localhost',
    'Hostname or ip address of the kegbot core to connect to.  If the special '
    'value "_auto_" is given (default), the program will attempt to locate '
    'the kegbot core automatically. ')

gflags.DEFINE_integer('kb_core_port', 9999,
    'Port number of host at --kb_core_hostname to connect to.  Note that this '
    'value is ignored if --kb_core_hostname=_auto_.')

gflags.DEFINE_string('client_name', 'mykegboard',
    'Name to use for this client connection.')


class ClientException(Exception):
  """A generic exception."""

class BaseClient:
  def __init__(self, server_addr=None, client_name=None):
    if server_addr is None:
      server_addr = (FLAGS.kb_core_hostname, FLAGS.kb_core_port)
    if client_name is None:
      client_name = FLAGS.client_name
    self._server_host, self._server_port = server_addr
    self._conn = None
    self._logger = logging.getLogger('kegnet-client')

  def _GetConnection(self):
    if self._conn is None:
      addr = (self._server_host, self._server_port)
      self._logger.info('Opening connection to %s:%i' % addr)
      self._conn = httplib.HTTPConnection(*addr)
    return self._conn

  def _ResetConnection(self):
    self._logger.info('Resetting connection')
    conn = self._conn
    self._conn = None
    if conn:
      try:
        conn.close()
      finally:
        pass

  def SendMessage(self, endpoint, message):
    params = message.AsDict()
    return self.Request(endpoint, params)

  def Request(self, endpoint, params=None, timeout=5, method='GET'):
    try:
      return self._Request(endpoint, params, timeout, method)
    except httplib.HTTPException, e:
      raise ClientException, str(e)
    except socket.error, e:
      raise ClientException, str(e)

  def _Request(self, endpoint, params=None, timeout=5, method='GET'):
    if params is not None:
      params = urllib.urlencode(params)
      endpoint = endpoint + '?' + params

    try:
      conn = self._GetConnection()
      self._logger.debug('sending request')
      conn.request(method, endpoint)
    except httplib.ImproperConnectionState, e:
      # 1 retry allowed
      self._logger.warning('Connection failed: %s' % (e,))
      self._ResetConnection()
      conn = self._GetConnection()
      self._logger.info('resending request')
      conn.request(method, endpoint)
    self._logger.debug('awaiting response')
    response = conn.getresponse()
    self._logger.debug('got response: %s' % response.status)

    if response.status != httplib.OK:
      print 'bad response:', response.status
    else:
      return response.read()

class KegnetClient(BaseClient):

  def SendFlowUpdate(self, tap_name, meter_reading):
    message = kegnet_message.FlowUpdateMessage(tap_name=tap_name,
        meter_reading=meter_reading)
    return self.SendMessage('flow/update', message)

  def SendFlowStart(self, tap_name):
    message = kegnet_message.FlowStartMessage(tap_name=tap_name)
    return self.SendMessage('flow/start', message)

  def SendFlowStop(self, tap_name):
    message = kegnet_message.FlowStopMessage(tap_name=tap_name)
    return self.SendMessage('flow/stop', message)
