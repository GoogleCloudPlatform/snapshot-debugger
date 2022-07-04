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
""" Unit test file for the permissions_rest_service module.
"""

import unittest

from snapshot_dbg_cli import data_formatter
from snapshot_dbg_cli.exceptions import SilentlyExitError
from snapshot_dbg_cli.permissions_rest_service import PermissionsRestService
from snapshot_dbg_cli.http_service import HttpService
from snapshot_dbg_cli.user_output import UserOutput

from io import StringIO
from unittest.mock import ANY
from unittest.mock import call
from unittest.mock import MagicMock
from unittest.mock import patch

TEST_PROJECT_ID = 'cli-test-project'


class PermissionsRestServiceTests(unittest.TestCase):
  """ Contains the unit tests for the PermissionsRestService class.
  """

  def setUp(self):
    self.http_service_mock = MagicMock(spec=HttpService)

    self.user_output_mock = MagicMock(
        wraps=UserOutput(
            is_debug_enabled=False,
            data_formatter=data_formatter.DataFormatter()))

    # A default test instance which tests are free to use, some tests will still
    # create their own custom version as needed.
    self.permissions_rest_service = PermissionsRestService(
        self.http_service_mock, TEST_PROJECT_ID, self.user_output_mock)

    # By default return a happy response, tests can customize when needed.  Here
    # happy means that all of the permissions being queried are sent back
    # indicating the user has those permissions on the project.
    def happy_response(method, url, data):
      del method
      del url
      return data

    self.http_service_mock.send_request = MagicMock(side_effect=happy_response)

  def test_uses_correct_url(self):
    service_project1 = PermissionsRestService(self.http_service_mock,
                                              'project1', self.user_output_mock)

    service_project2 = PermissionsRestService(self.http_service_mock,
                                              'project2', self.user_output_mock)

    expected_url = ('https://cloudresourcemanager.googleapis.com/v1/projects'
                    '/{}:testIamPermissions')
    expected_url1 = expected_url.format('project1')
    expected_url2 = expected_url.format('project2')

    service_project1.test_iam_permissions(['foo.permission'])
    service_project2.test_iam_permissions(['foo.permission'])

    self.assertEqual([
        call(ANY, expected_url1, data=ANY),
        call(ANY, expected_url2, data=ANY)
    ], self.http_service_mock.send_request.mock_calls)

  def test_test_iam_permissions_uses_post(self):
    self.permissions_rest_service.test_iam_permissions(['foo.permission'])
    self.http_service_mock.send_request.assert_called_once_with(
        'POST', ANY, data=ANY)

  def test_test_iam_permissions_uses_currect_request_data(self):
    self.permissions_rest_service.test_iam_permissions(['foo1.perm'])
    self.permissions_rest_service.test_iam_permissions(
        ['foo1.perm', 'foo2.perm'])

    self.assertEqual([
        call(ANY, ANY, data={'permissions': ['foo1.perm']}),
        call(ANY, ANY, data={'permissions': ['foo1.perm', 'foo2.perm']})
    ], self.http_service_mock.send_request.mock_calls)

  def test_test_iam_permissions_throws_on_bad_response(self):
    # The response needs to be a dict, and if it's a dict and it has the
    # 'permissions' key, it should map to a list.
    testcases = [
        [],
        'foo',
        {
            'permissions': 'foo'
        },
    ]

    for response in testcases:
      with self.subTest(response):
        with self.assertRaises(SilentlyExitError), \
             patch('sys.stdout', new_callable=StringIO) as out, \
             patch('sys.stderr', new_callable=StringIO) as err:
          self.http_service_mock.send_request = MagicMock(return_value=response)
          self.permissions_rest_service.test_iam_permissions(['foo'])
          self.assertIn(
              'testIamPermissions did not return the expected response',
              err.getvalue())
          self.assertEqual('', out)

  def test_test_iam_permissions_works_as_expected(self):
    testcases = [
        # (Test name, Requested Perms, Response Perms, Expected Return Value)
        ('Fails 1', ['p1'], [], (False, {'p1'})),
        ('Fails 2', ['p1', 'p2'], [], (False, {'p1', 'p2'})),
        ('Fails 3', ['p1', 'p2'], ['p1'], (False, {'p2'})),
        ('Fails 4', ['p1', 'p2'], ['p2'], (False, {'p1'})),
        ('Fails 5', ['p1', 'p2', 'p3'], [], (False, {'p1', 'p2', 'p3'})),
        ('Fails 6', ['p1', 'p2', 'p3'], ['p1'], (False, {'p2', 'p3'})),
        ('Fails 7', ['p1', 'p2', 'p3'], ['p2'], (False, {'p1', 'p3'})),
        ('Fails 8', ['p1', 'p2', 'p3'], ['p3'], (False, {'p1', 'p2'})),
        ('Fails 9', ['p1', 'p2', 'p3'], ['p1', 'p2'], (False, {'p3'})),
        ('Fails 10', ['p1', 'p2', 'p3'], ['p1', 'p3'], (False, {'p2'})),
        ('Fails 11', ['p1', 'p2', 'p3'], ['p2', 'p3'], (False, {'p1'})),
        ('Success 1', ['p1'], ['p1'], (True, set())),
        ('Success 2', ['p1', 'p2'], ['p1', 'p2'], (True, set())),
        ('Success 3', ['p1', 'p2', 'p3'], ['p1', 'p2', 'p3'], (True, set())),
    ]

    for testname, req_perms, resp_perms, expected_return_value in testcases:
      with self.subTest(testname):
        self.http_service_mock.send_request = MagicMock(
            return_value={'permissions': resp_perms})
        self.assertEqual(
            expected_return_value,
            self.permissions_rest_service.test_iam_permissions(req_perms))

  def test_check_required_permissions_raises_when_required_perms_missing(self):
    self.http_service_mock.send_request = MagicMock(
        return_value={'permissions': []})

    with self.assertRaises(SilentlyExitError), \
         patch('sys.stdout', new_callable=StringIO) as out, \
         patch('sys.stderr', new_callable=StringIO) as err:
      self.permissions_rest_service.check_required_permissions(['foo'])

    self.assertIn(
        'For the requested operation, the user is missing the following '
        'required permissions on project cli-test-project.',
        ' '.join(err.getvalue().split()))
    self.assertIn("{'foo'}", err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_check_required_permissions_returns_normally_when_perms_ok(self):
    # By default the http mock is setup to return all supplied permissions, so
    # there is not mocks to setup here.
    with patch('sys.stdout', new_callable=StringIO) as out, \
         patch('sys.stderr', new_callable=StringIO) as err:
      self.permissions_rest_service.check_required_permissions(['foo'])
      self.permissions_rest_service.check_required_permissions(['foo', 'bar'])

    # If we get here, that means the calls did not throw, so that's part of the
    # test. We'll also ensure nothing was output to stderr or stdout.
    self.assertEqual('', err.getvalue())
    self.assertEqual('', out.getvalue())
