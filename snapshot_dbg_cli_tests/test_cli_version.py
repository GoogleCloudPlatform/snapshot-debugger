# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
""" Unit test file for the cli_version module.
"""

import unittest
import urllib

import snapshot_dbg_cli.cli_version

from email.message import EmailMessage
from io import BytesIO
from io import StringIO
from unittest.mock import ANY
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.error import URLError


class CliVersionTests(unittest.TestCase):
  """ Contains the unit tests for the cli_version module.
  """

  def setUp(self):
    self.urlopen_patcher = patch(
        'snapshot_dbg_cli.http_service.urlopen', autospec=True)
    self.urlopen_mock = self.urlopen_patcher.start()
    self.addCleanup(self.urlopen_patcher.stop)

    # Just to have a default return value set, tests that care will update it.
    self.set_urlopen_response('foo')

  def set_urlopen_response(self, body):
    # The EmailMessage here may look odd, but the response headers are "...in
    # the form of an EmailMessage instance."
    # https://docs.python.org/3/library/urllib.request.html#urllib.response.addinfourl.headers,
    response_headers = EmailMessage()
    response_headers.add_header('Content-type', 'text/plain; charset=utf-8')
    resp = urllib.response.addinfourl(
        BytesIO(body.encode('utf-8')), response_headers, url='https://foo.com')
    resp.code = 200
    resp.msg = 'OK'
    self.urlopen_mock.return_value = resp

  def set_urlopen_exception(self, exception):
    self.urlopen_mock.side_effect = exception

  def test_running_version_is_expected_value(self):
    snapshot_dbg_cli.cli_version.VERSION = 'SNAPSHOT_DEBUGGER_CLI_VERSION_0_1_1'
    self.assertEqual('0.1.1', snapshot_dbg_cli.cli_version.running_version())

  def test_latest_version_retrieves_expected_version(self):
    testcases = [
        ('Test 1', 'SNAPSHOT_DEBUGGER_CLI_VERSION_0_1_2', '0.1.2'),
        ('Test 2', 'fooSNAPSHOT_DEBUGGER_CLI_VERSION_2_1_0foo', '2.1.0'),

        # If the pattern is not found, None is expected to be returned.
        ('Test 3', 'foo', None),
        ('Test 4', 'SNAPSHOT_DEBUGGER_CLI_VERSION_', None),
        ('Test 5', 'SNAPSHOT_DEBUGGER_CLI_VERSION_1', None),
        ('Test 6', 'SNAPSHOT_DEBUGGER_CLI_VERSION_1_1', None),
        ('Test 7', 'SNAPSHOT_DEBUGGER_CLI_VERSION_1_1_a', None),
        ('Test 8', 'SNAPSHOT_DEBUGGER_CLI_VERSION_a_1_0', None),
    ]

    for testname, response, expected_version in testcases:
      with self.subTest(testname):
        self.set_urlopen_response(response)
        self.assertEqual(expected_version,
                         snapshot_dbg_cli.cli_version.latest_version())

  def test_latest_version_handles_http_failure_as_expected(self):
    testcases = [
        ('HTTP Error',
         HTTPError('https://foo.com', 500, 'Internal Server Error', {},
                   BytesIO(b'Fake Error Message'))),
        ('URL Error', URLError('URLError Fake Error Message')),
        ('Timeout Error', TimeoutError()),
    ]

    for testname, exception in testcases:
      with self.subTest(testname):
        with patch('sys.stdout', new_callable=StringIO) as out, \
             patch('sys.stderr', new_callable=StringIO) as err:

          self.set_urlopen_exception(exception)
          self.assertEqual(None, snapshot_dbg_cli.cli_version.latest_version())
          self.assertEqual('', err.getvalue())
          self.assertEqual('', out.getvalue())

  def test_latest_version_no_http_retries(self):
    self.set_urlopen_exception(
        HTTPError('https://foo.com', 500, 'Internal Server Error', {},
                  BytesIO(b'Fake Error Message')))

    snapshot_dbg_cli.cli_version.latest_version()

    # Retries should be 0, so there should only be 1 call.
    self.assertEqual(1, self.urlopen_mock.call_count)

  def test_latest_version_http_timeout_is_as_epected(self):
    snapshot_dbg_cli.cli_version.latest_version()
    self.urlopen_mock.assert_called_once_with(ANY, timeout=5)

  def test_latest_version_uses_expected_request(self):
    snapshot_dbg_cli.cli_version.latest_version()
    request = self.urlopen_mock.call_args[0][0]
    self.assertEqual('GET', request.method)
    self.assertEqual(
        'https://raw.githubusercontent.com/GoogleCloudPlatform/'
        'snapshot-debugger/main/snapshot_dbg_cli/cli_version.py',
        request.full_url)
    self.assertFalse(request.has_header('Authorization'))

  def test_check_for_newer_version_works_as_expected(self):
    testcases = [
        ('Test 1', '0_1_2', '0_1_2', False),
        ('Test 2', '0_1_3', '0_1_2', False),
        ('Test 3', '0_1_10', '0_1_2', False),
        ('Test 4', '0_10_2', '0_2_2', False),
        ('Test 5', '10_2_2', '2_2_2', False),
        ('Test 6', '0_1_2', '0_1_3', True),
        ('Test 7', '0_1_2', '0_1_10', True),
        ('Test 8', '0_2_2', '0_10_2', True),
        ('Test 9', '2_2_2', '10_2_2', True),
    ]

    for testname, running_version, latest_version, \
        should_emit_warning in testcases:
      with self.subTest(testname):
        with patch('sys.stdout', new_callable=StringIO) as out, \
             patch('sys.stderr', new_callable=StringIO) as err:
          snapshot_dbg_cli.cli_version.VERSION = (
              f'SNAPSHOT_DEBUGGER_CLI_VERSION_{running_version}')
          self.set_urlopen_response(
              f'SNAPSHOT_DEBUGGER_CLI_VERSION_{latest_version}')
          snapshot_dbg_cli.cli_version.check_for_newer_version()

          if should_emit_warning:
            self.assertIn(('A newer version of the CLI is available '
                           f'({latest_version.replace("_", ".")} vs '
                           f'{running_version.replace("_", ".")})'),
                          err.getvalue())
          else:
            self.assertEqual('', err.getvalue())

          self.assertEqual('', out.getvalue())

  def test_check_for_newer_version_latest_version_not_found(self):
    with patch('sys.stdout', new_callable=StringIO) as out, \
         patch('sys.stderr', new_callable=StringIO) as err:

      # If no version was able to be determined we expect the code to simply
      # exit without writing anything to stdout/stderr
      self.set_urlopen_response('No version set.')
      snapshot_dbg_cli.cli_version.check_for_newer_version()
      self.assertEqual('', err.getvalue())
      self.assertEqual('', out.getvalue())
