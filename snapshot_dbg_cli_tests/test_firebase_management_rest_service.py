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
""" Unit test file for the firebase_management_rest_service module.
"""

import copy
import json
import unittest

from snapshot_dbg_cli import data_formatter
from snapshot_dbg_cli.exceptions import SilentlyExitError
from snapshot_dbg_cli.firebase_management_rest_service import FirebaseManagementRestService
from snapshot_dbg_cli.firebase_types import DatabaseCreateStatus
from snapshot_dbg_cli.firebase_types import DatabaseGetStatus
from snapshot_dbg_cli.firebase_types import FirebaseProjectStatus
from snapshot_dbg_cli.http_service import HttpService
from snapshot_dbg_cli.user_output import UserOutput

from io import BytesIO
from io import StringIO
from unittest.mock import call
from unittest.mock import MagicMock
from unittest.mock import patch
from urllib.error import HTTPError

TEST_PROJECT_ID = 'cli-test-project'

VALID_PROJECT_RESPONSE = {'state': 'ACTIVE'}

DB_NAME = "projects/1111111111/locations/us-central1/instances/db-name"

VALID_DB_RESPONSE = {
    'name': DB_NAME,
    'project': 'project-name',
    'databaseUrl': 'project-default-rtdb.firebaseio.com',
    'type': 'DEFAULT_DATABASE',
    'state': 'ACTIVE'
}


class FirebaseManagementRestServiceTests(unittest.TestCase):
  """ Contains the unit tests for the FirebaseManagementRestService class.
  """

  def setUp(self):
    self.http_service_mock = MagicMock(spec=HttpService)

    self.user_output_mock = MagicMock(
        wraps=UserOutput(
            is_debug_enabled=False,
            data_formatter=data_formatter.DataFormatter()))

    # A default test instance which tests are free to use, some tests will still
    # create their own custom version as needed.
    self.firebase_management_rest_service = FirebaseManagementRestService(
        self.http_service_mock, TEST_PROJECT_ID, self.user_output_mock)

  def test_project_get_builds_correct_http_request(self):
    self.http_service_mock.send.return_value = VALID_PROJECT_RESPONSE

    service1 = FirebaseManagementRestService(self.http_service_mock, 'project1',
                                             self.user_output_mock)
    service2 = FirebaseManagementRestService(self.http_service_mock, 'project2',
                                             self.user_output_mock)

    expected_url = ('https://firebase.googleapis.com/v1beta1/projects/{}')
    expected_url1 = expected_url.format('project1')
    expected_url2 = expected_url.format('project2')

    service1.project_get()
    service2.project_get()

    self.assertEqual([
        call('GET', expected_url1, include_project_header=True),
        call('GET', expected_url2, include_project_header=True),
    ], self.http_service_mock.build_request.mock_calls)

  def test_project_get_calls_http_send_with_expected_parameters(self):
    self.http_service_mock.send.return_value = VALID_PROJECT_RESPONSE
    self.http_service_mock.build_request.return_value = 'http request object'

    self.firebase_management_rest_service.project_get()

    self.http_service_mock.send.assert_called_once_with(
        'http request object', handle_http_error=False)

  def test_project_get_returns_status_not_enabled_on_404(self):
    http_error = HTTPError('https://foo.com', 404, 'Not Found', {}, None)
    self.http_service_mock.send.side_effect = http_error

    obtained_response = self.firebase_management_rest_service.project_get()

    self.assertEqual(FirebaseProjectStatus.NOT_ENABLED,
                     obtained_response.status)

  def test_project_get_raises_on_non_404(self):
    http_error = HTTPError('https://foo.com', 500, 'Internal Server Error', {},
                           BytesIO(b'Fake Error Message'))
    self.http_service_mock.send.side_effect = http_error

    with self.assertRaises(SilentlyExitError), \
         patch('sys.stdout', new_callable=StringIO) as out, \
         patch('sys.stderr', new_callable=StringIO) as err:
      self.firebase_management_rest_service.project_get()

    self.assertIn('Fake Error Message', err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_project_get_raises_when_state_is_missing_in_response(self):
    self.http_service_mock.send.return_value = {
        'test': 'bad response no state field'
    }

    with self.assertRaises(SilentlyExitError), \
         patch('sys.stdout', new_callable=StringIO) as out, \
         patch('sys.stderr', new_callable=StringIO) as err:
      self.firebase_management_rest_service.project_get()

    self.assertIn(
        "ERROR. Expected to find the 'state' field populated in the projects "
        "get response with a value of 'ACTIVE'.",
        ' '.join(err.getvalue().split()))
    self.assertIn("{'test': 'bad response no state field'}", err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_project_get_raises_when_state_is_not_active_in_response(self):
    self.http_service_mock.send.return_value = {'state': 'DISABLED'}

    with self.assertRaises(SilentlyExitError), \
         patch('sys.stdout', new_callable=StringIO) as out, \
         patch('sys.stderr', new_callable=StringIO) as err:
      self.firebase_management_rest_service.project_get()

    self.assertIn(
        "ERROR. Expected to find the 'state' field populated in the projects "
        "get response with a value of 'ACTIVE'.",
        ' '.join(err.getvalue().split()))
    self.assertIn("{'state': 'DISABLED'}", err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_project_returns_expected_value_on_success(self):
    mock_response = {
        'state': 'ACTIVE',
        'resources': {
            'realtimeDatabaseInstance': 'foo-db-instance'
        }
    }
    self.http_service_mock.send.return_value = mock_response

    obtained_response = self.firebase_management_rest_service.project_get()

    self.assertEqual(FirebaseProjectStatus.ENABLED, obtained_response.status)
    self.assertEqual('foo-db-instance',
                     obtained_response.firebase_project.default_rtdb_instance)

  def test_rtdb_instance_get_builds_correct_http_request(self):
    self.http_service_mock.send.return_value = VALID_DB_RESPONSE
    service1 = FirebaseManagementRestService(self.http_service_mock, 'project1',
                                             self.user_output_mock)
    service2 = FirebaseManagementRestService(self.http_service_mock, 'project2',
                                             self.user_output_mock)

    expected_url = ('https://firebasedatabase.googleapis.com/v1beta/projects/'
                    '{}/locations/-/instances/{}')
    expected_url1 = expected_url.format('project1', 'db1')
    expected_url2 = expected_url.format('project2', 'db2')

    service1.rtdb_instance_get('db1')
    service2.rtdb_instance_get('db2')

    self.assertEqual([
        call('GET', expected_url1, include_project_header=True),
        call('GET', expected_url2, include_project_header=True),
    ], self.http_service_mock.build_request.mock_calls)

  def test_rtdb_instance_get_calls_http_send_with_expected_parameters(self):
    self.http_service_mock.send.return_value = VALID_DB_RESPONSE
    self.http_service_mock.build_request.return_value = 'http request object'

    self.firebase_management_rest_service.rtdb_instance_get('db-name')

    self.http_service_mock.send.assert_called_once_with(
        'http request object', handle_http_error=False)

  def test_rtdb_instance_get_returns_status_not_enabled_on_404(self):
    http_error = HTTPError('https://foo.com', 404, 'Not Found', {},
                           BytesIO(b'Fake Error Message'))
    self.http_service_mock.send.side_effect = http_error

    obtained_response = self.firebase_management_rest_service.rtdb_instance_get(
        'db-name')

    self.assertEqual(DatabaseGetStatus.DOES_NOT_EXIST, obtained_response.status)

  def test_rtdb_instance_get_raises_on_non_404(self):
    http_error = HTTPError('https://foo.com', 500, 'Internal Server Error', {},
                           BytesIO(b'Fake Error Message'))
    self.http_service_mock.send.side_effect = http_error

    with self.assertRaises(SilentlyExitError), \
         patch('sys.stdout', new_callable=StringIO) as out, \
         patch('sys.stderr', new_callable=StringIO) as err:
      self.firebase_management_rest_service.rtdb_instance_get('db-name')

    self.assertIn('Fake Error Message', err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_rtdb_instance_get_raises_when_field_missing_in_response(self):
    # To note, the field checking actually occurs in DatabaseInstance class
    # clode. Here we just choose to make one expected field be missing, and
    # ensure the exception propagates out of the get method.
    mock_response = copy.deepcopy(VALID_DB_RESPONSE)
    del mock_response['state']

    self.http_service_mock.send.return_value = mock_response

    with self.assertRaises(SilentlyExitError), \
         patch('sys.stdout', new_callable=StringIO) as out, \
         patch('sys.stderr', new_callable=StringIO) as err:
      self.firebase_management_rest_service.rtdb_instance_get('db-name')

    self.assertIn("DatabaseInstance is missing expected field 'state'",
                  err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_rtdb_instance_get_raises_when_state_is_not_active_in_response(self):
    mock_response = copy.deepcopy(VALID_DB_RESPONSE)
    mock_response['state'] = 'DISABLED'

    self.http_service_mock.send.return_value = mock_response

    with self.assertRaises(SilentlyExitError), \
         patch('sys.stdout', new_callable=StringIO) as out, \
         patch('sys.stderr', new_callable=StringIO) as err:
      self.firebase_management_rest_service.rtdb_instance_get('db-name')

    self.assertIn(
        "ERROR. Expected to find the 'state' field populated in the database "
        "instance response with a value of 'ACTIVE'.",
        ' '.join(err.getvalue().split()))
    self.assertIn("'state': 'DISABLED'", err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_rtdb_instance_get_returns_expected_value_on_success(self):
    self.http_service_mock.send.return_value = {
        'name': DB_NAME,
        'project': 'project-name',
        'databaseUrl': 'project-default-rtdb.firebaseio.com',
        'type': 'DEFAULT_DATABASE',
        'state': 'ACTIVE'
    }

    obtained_response = self.firebase_management_rest_service.rtdb_instance_get(
        'db-name')

    self.assertEqual(DatabaseGetStatus.EXISTS, obtained_response.status)
    self.assertEqual(DB_NAME, obtained_response.database_instance.name)
    self.assertEqual('project-name',
                     obtained_response.database_instance.project)
    self.assertEqual('project-default-rtdb.firebaseio.com',
                     obtained_response.database_instance.database_url)
    self.assertEqual('DEFAULT_DATABASE',
                     obtained_response.database_instance.type)
    self.assertEqual('ACTIVE', obtained_response.database_instance.state)

  def test_rtdb_instance_create_builds_correct_http_request(self):
    self.http_service_mock.send.return_value = VALID_DB_RESPONSE
    service1 = FirebaseManagementRestService(self.http_service_mock, 'project1',
                                             self.user_output_mock)
    service2 = FirebaseManagementRestService(self.http_service_mock, 'project2',
                                             self.user_output_mock)

    expected_url = ('https://firebasedatabase.googleapis.com/v1beta/'
                    'projects/{}/locations/{}/instances')

    expected_url1 = expected_url.format('project1', 'us-central1')
    expected_url2 = expected_url.format('project2', 'test-loc')

    service1.rtdb_instance_create('db1-cdbg', 'us-central1')
    service2.rtdb_instance_create('db2-default-rtdb', 'test-loc')

    self.assertEqual([
        call(
            'POST',
            expected_url1,
            include_project_header=True,
            parameters=['databaseId=db1-cdbg'],
            data={'type': 'USER_DATABASE'}),
        call(
            'POST',
            expected_url2,
            include_project_header=True,
            parameters=['databaseId=db2-default-rtdb'],
            data={'type': 'DEFAULT_DATABASE'}),
    ], self.http_service_mock.build_request.mock_calls)

  def test_rtdb_instance_create_calls_http_send_with_expected_parameters(self):
    self.http_service_mock.send.return_value = VALID_DB_RESPONSE
    self.http_service_mock.build_request.return_value = 'http request object'

    self.firebase_management_rest_service.rtdb_instance_create(
        'db-name', 'test-loc')

    self.http_service_mock.send.assert_called_once_with(
        'http request object', max_retries=0, handle_http_error=False)

  def test_rtdb_instance_create_returns_status_failed_precondition(self):
    error_message = json.dumps({'error': {'status': 'FAILED_PRECONDITION'}})

    http_error = HTTPError('https://foo.com', 400, 'Not Found', {},
                           BytesIO(bytes(f'{error_message}', 'utf-8')))
    self.http_service_mock.send.side_effect = http_error

    obtained_response = \
      self.firebase_management_rest_service.rtdb_instance_create(
        'db-name', 'us-central1')

    self.assertEqual(DatabaseCreateStatus.FAILED_PRECONDITION,
                     obtained_response.status)

  def test_rtdb_instance_create_returns_status_invalid_argument(self):
    error_message = json.dumps({'error': {'status': 'INVALID_ARGUMENT', 'message': 'Invalid location "bad-location"'}})

    http_error = HTTPError('https://foo.com', 400, 'Invalid Argument', {},
                           BytesIO(bytes(f'{error_message}', 'utf-8')))

    self.http_service_mock.send.side_effect = http_error

    with self.assertRaises(SilentlyExitError), \
         patch('sys.stdout', new_callable=StringIO) as out, \
         patch('sys.stderr', new_callable=StringIO) as err:
      self.firebase_management_rest_service.rtdb_instance_create(
          'db-name', 'bad-location')

    self.assertIn('Invalid location', err.getvalue())
    self.assertIn((
        'One potential reason for this is if an invalid location was specified, '
        'valid locations for RTDBs can be found at '
        'https://firebase.google.com/docs/projects/locations#rtdb-locations.'),
        err.getvalue())

    self.assertEqual('', out.getvalue())

  def test_rtdb_instance_create_raises_on_400_non_special_type(self):
    http_error = HTTPError('https://foo.com', 400, 'Internal Server Error', {},
                           BytesIO(b'Fake Error Message'))
    self.http_service_mock.send.side_effect = http_error

    with self.assertRaises(SilentlyExitError), \
         patch('sys.stdout', new_callable=StringIO) as out, \
         patch('sys.stderr', new_callable=StringIO) as err:
      self.firebase_management_rest_service.rtdb_instance_create(
          'db-name', 'us-central1')

    self.assertIn('Fake Error Message', err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_rtdb_instance_create_raises_on_non_400(self):
    http_error = HTTPError('https://foo.com', 500, 'Internal Server Error', {},
                           BytesIO(b'Fake Error Message'))
    self.http_service_mock.send.side_effect = http_error

    with self.assertRaises(SilentlyExitError), \
         patch('sys.stdout', new_callable=StringIO) as out, \
         patch('sys.stderr', new_callable=StringIO) as err:
      self.firebase_management_rest_service.rtdb_instance_create(
          'db-name', 'us-central1')

    self.assertIn('Fake Error Message', err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_rtdb_instance_create_returns_expected_value_on_success(self):
    self.http_service_mock.send.return_value = {
        'name': DB_NAME,
        'project': 'project-name',
        'databaseUrl': 'project-default-rtdb.firebaseio.com',
        'type': 'DEFAULT_DATABASE',
        'state': 'ACTIVE'
    }

    obtained_response = \
        self.firebase_management_rest_service.rtdb_instance_create(
          'db-name', 'us-central1')

    self.assertEqual(DatabaseCreateStatus.SUCCESS, obtained_response.status)
    self.assertEqual(DB_NAME, obtained_response.database_instance.name)
    self.assertEqual('project-name',
                     obtained_response.database_instance.project)
    self.assertEqual('project-default-rtdb.firebaseio.com',
                     obtained_response.database_instance.database_url)
    self.assertEqual('DEFAULT_DATABASE',
                     obtained_response.database_instance.type)
    self.assertEqual('ACTIVE', obtained_response.database_instance.state)
