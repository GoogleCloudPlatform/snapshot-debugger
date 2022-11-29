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
""" Unit test file for the firebase_rtdb_rest_service module.
"""

import unittest

from snapshot_dbg_cli import data_formatter
from snapshot_dbg_cli.firebase_rtdb_rest_service import FirebaseRtdbRestService
from snapshot_dbg_cli.http_service import HttpService
from snapshot_dbg_cli.user_output import UserOutput

from unittest.mock import call
from unittest.mock import MagicMock
from unittest.mock import ANY

TEST_URL = 'https://cli-test-project1-cdbg.firebaseio.com'


class FirebaseRtdbRestServiceTests(unittest.TestCase):
  """ Contains the unit tests for the FirebaseRtdbRestService class.
  """

  def setUp(self):
    self.http_service_mock = MagicMock(spec=HttpService)

    self.user_output_mock = MagicMock(
        wraps=UserOutput(
            is_debug_enabled=False,
            data_formatter=data_formatter.DataFormatter()))

    # A default test instance which tests are free to use, some tests will still
    # create their own custom version as needed.
    self.firebase_rtdb_rest_service = FirebaseRtdbRestService(
        self.http_service_mock, TEST_URL, self.user_output_mock)

  def test_build_rtdb_url_works_as_expected(self):
    self.assertEqual(
        'https://cli-test-project-cdbg.firebaseio.com/cdbg/debuggees.json',
        FirebaseRtdbRestService(
            self.http_service_mock,
            'https://cli-test-project-cdbg.firebaseio.com',
            self.user_output_mock).build_rtdb_url('cdbg/debuggees'))

    self.assertEqual(
        'https://foo-default-rtdb.firebaseio.com/cdbg/breakpoints/active.json',
        FirebaseRtdbRestService(
            self.http_service_mock, 'https://foo-default-rtdb.firebaseio.com',
            self.user_output_mock).build_rtdb_url('cdbg/breakpoints/active'))

  def test_get_works_as_expected(self):
    # In this test we don't check the shallow or extra_retry_codes parameters,
    # it is covered in its own test.
    expected_calls = [
        call(
            'GET',
            self.firebase_rtdb_rest_service.build_rtdb_url('cdbg/debuggees'),
            extra_retry_codes=ANY,
            parameters=ANY),
        call(
            'GET',
            self.firebase_rtdb_rest_service.build_rtdb_url(
                'cdbg/breakpoints/active'),
            extra_retry_codes=ANY,
            parameters=ANY),
    ]

    self.http_service_mock.send_request = MagicMock(side_effect=['1', '2'])

    response1 = self.firebase_rtdb_rest_service.get('cdbg/debuggees')
    response2 = self.firebase_rtdb_rest_service.get('cdbg/breakpoints/active')

    self.assertEqual(expected_calls,
                     self.http_service_mock.send_request.mock_calls)
    self.assertEqual('1', response1)
    self.assertEqual('2', response2)

  def test_get_shallow_param_works_as_expected(self):
    expected_calls = [
        call('GET', ANY, extra_retry_codes=ANY, parameters=[]),
        call('GET', ANY, extra_retry_codes=ANY, parameters=[]),
        call('GET', ANY, extra_retry_codes=ANY, parameters=['shallow=true']),
    ]

    self.firebase_rtdb_rest_service.get('cdbg/debuggees')
    self.firebase_rtdb_rest_service.get('cdbg/debuggees', shallow=False)
    self.firebase_rtdb_rest_service.get('cdbg/debuggees', shallow=True)

    self.assertEqual(expected_calls,
                     self.http_service_mock.send_request.mock_calls)

  def test_get_extra_retry_codes_param_works_as_expected(self):
    expected_calls = [
        call('GET', ANY, extra_retry_codes=None, parameters=ANY),
        call('GET', ANY, extra_retry_codes=[404], parameters=ANY),
        call('GET', ANY, extra_retry_codes=[404, 405], parameters=ANY),
    ]

    self.firebase_rtdb_rest_service.get('')
    self.firebase_rtdb_rest_service.get(
        '', shallow=None, extra_retry_codes=[404])
    self.firebase_rtdb_rest_service.get(
        '', shallow=None, extra_retry_codes=[404, 405])

    self.assertEqual(expected_calls,
                     self.http_service_mock.send_request.mock_calls)

  def test_set_works_as_expected(self):
    expected_calls = [
        call(
            'PUT',
            self.firebase_rtdb_rest_service.build_rtdb_url('cdbg/debuggees'),
            data='data1',
            max_retries=0),
        call(
            'PUT',
            self.firebase_rtdb_rest_service.build_rtdb_url(
                'cdbg/breakpoints/active'),
            data='data2',
            max_retries=0)
    ]

    self.http_service_mock.send_request = MagicMock(side_effect=['1', '2'])

    response1 = self.firebase_rtdb_rest_service.set('cdbg/debuggees', 'data1')
    response2 = self.firebase_rtdb_rest_service.set('cdbg/breakpoints/active',
                                                    'data2')

    self.assertEqual(expected_calls,
                     self.http_service_mock.send_request.mock_calls)
    self.assertEqual('1', response1)
    self.assertEqual('2', response2)

  def test_delete_works_as_expected(self):
    expected_calls = [
        call(
            'DELETE',
            self.firebase_rtdb_rest_service.build_rtdb_url(
                'cdbg/debuggees/123'),
            max_retries=5),
        call(
            'DELETE',
            self.firebase_rtdb_rest_service.build_rtdb_url(
                'cdbg/breakpoints/active/b-123'),
            max_retries=5)
    ]

    self.http_service_mock.send_request = MagicMock(return_value=None)

    response1 = self.firebase_rtdb_rest_service.delete('cdbg/debuggees/123')
    response2 = self.firebase_rtdb_rest_service.delete(
        'cdbg/breakpoints/active/b-123')

    self.assertEqual(expected_calls,
                     self.http_service_mock.send_request.mock_calls)
    self.assertEqual(None, response1)
    self.assertEqual(None, response2)
