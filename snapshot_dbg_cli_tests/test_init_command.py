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
""" Unit test file for the InitCommand class.
"""

import os
import sys
import unittest
from io import StringIO

from snapshot_dbg_cli import cli_run
from snapshot_dbg_cli import data_formatter
from snapshot_dbg_cli.cli_services import CliServices
from snapshot_dbg_cli.gcloud_cli_service import GcloudCliService
from snapshot_dbg_cli.firebase_types import DatabaseGetResponse
from snapshot_dbg_cli.firebase_types import DatabaseGetStatus
from snapshot_dbg_cli.firebase_types import DatabaseInstance
from snapshot_dbg_cli.firebase_types import DatabaseCreateResponse
from snapshot_dbg_cli.firebase_types import DatabaseCreateStatus
from snapshot_dbg_cli.firebase_types import FirebaseProject
from snapshot_dbg_cli.firebase_types import FirebaseProjectGetResponse
from snapshot_dbg_cli.firebase_types import FirebaseProjectStatus
from snapshot_dbg_cli.firebase_management_rest_service import FirebaseManagementRestService
from snapshot_dbg_cli.firebase_rtdb_rest_service import FirebaseRtdbRestService
from snapshot_dbg_cli.permissions_rest_service import PermissionsRestService
from snapshot_dbg_cli.snapshot_debugger_rtdb_service import SnapshotDebuggerRtdbService
from snapshot_dbg_cli.user_output import UserOutput

from snapshot_dbg_cli.exceptions import SilentlyExitError

from unittest.mock import call
from unittest.mock import MagicMock
from unittest.mock import patch

TEST_PROJECT_ID = 'cli-test-project'


def build_firebase_project(defaut_rtdb_name=None):
  project_data = {'resources': {}}

  if defaut_rtdb_name is not None:
    project_data['resources']['realtimeDatabaseInstance'] = defaut_rtdb_name

  return FirebaseProject(project_data)


def build_database_instance(db_name, db_type, location='us-central1'):
  return DatabaseInstance({
      'name': f'projects/1111111111/locations/{location}/instances/{db_name}',
      'project': 'projects/1111111111',

      # Note, in practise, the domain is dependent on the location, however for
      # our purposes here we don't need to get that specific and simply use
      # firebaseio.com. For reference the actual domains used for the supported
      # regions can be found at:
      # https://firebase.google.com/docs/projects/locations#rtdb-locations
      'databaseUrl': f'https://{db_name}.firebaseio.com',
      'type': db_type,
      'state': 'ACTIVE'
  })


class InitCommandTests(unittest.TestCase):
  """ Contains the unit tests for the GetSnapshot class.
  """

  def setUp(self):
    self.cli_services = MagicMock(spec=CliServices)

    self.data_formatter = data_formatter.DataFormatter()
    self.cli_services.data_formatter = self.data_formatter

    # By wrapping a real UserOutput instance, we can test the method calls etc,
    # and it will still perform the actual stdout/stderr output which we can
    # also check when desired.
    self.user_output_mock = MagicMock(
        wraps=UserOutput(
            is_debug_enabled=False,
            data_formatter=data_formatter.DataFormatter()))
    self.cli_services.user_output = self.user_output_mock

    self.cli_services.project_id = TEST_PROJECT_ID

    self.gcloud_service_mock = MagicMock(spec=GcloudCliService)
    self.cli_services.gcloud_service = self.gcloud_service_mock

    self.permissions_service_mock = MagicMock(spec=PermissionsRestService)
    self.cli_services.permissions_service = self.permissions_service_mock

    self.firebase_management_service_mock = MagicMock(
        spec=FirebaseManagementRestService)
    self.cli_services.firebase_management_service = \
        self.firebase_management_service_mock

    self.firebase_rtdb_service_mock = MagicMock(spec=FirebaseRtdbRestService)
    self.cli_services.get_firebase_rtdb_rest_service = MagicMock(
        return_value=self.firebase_rtdb_service_mock)

    self.debugger_rtdb_service_mock = MagicMock(
        spec=SnapshotDebuggerRtdbService)
    self.cli_services.get_snapshot_debugger_rtdb_service = MagicMock(
        return_value=self.debugger_rtdb_service_mock)

    self.cli_services.get_snapshot_debugger_default_database_id = MagicMock(
        return_value=f'{TEST_PROJECT_ID}-cdbg')
    self.cli_services.get_firebase_default_rtdb_id = MagicMock(
        return_value=f'{TEST_PROJECT_ID}-default-rtdb')

    # Install a default happy path set of responses to mimic a project that is
    # already fully configured to minimize duplicating uninteresting parts of
    # the tests. The tests will override these defaults when appropriate.
    self.gcloud_service_mock.is_api_enabled = MagicMock(return_value=True)

    self.firebase_management_service_mock.project_get = MagicMock(
        return_value=FirebaseProjectGetResponse(FirebaseProjectStatus.ENABLED,
                                                build_firebase_project()))

    self.firebase_management_service_mock.rtdb_instance_get = MagicMock(
        return_value=DatabaseGetResponse(
            status=DatabaseGetStatus.EXISTS,
            database_instance=build_database_instance(TEST_PROJECT_ID,
                                                      'USER_DATABASE')))

    self.debugger_rtdb_service_mock.get_schema_version = MagicMock(
        return_value='1')

  def run_cmd(self, testargs, expected_exception=None):
    args = ['cli-test', 'init'] + testargs

    # We patch os.environ as some cli arguments can come from environment
    # variables, and if they happen to be set in the terminal running the tests
    # it will affect things.
    with patch.object(sys, 'argv', args), \
         patch.dict(os.environ, {}, clear=True), \
         patch('sys.stdout', new_callable=StringIO) as out, \
         patch('sys.stderr', new_callable=StringIO) as err:
      if expected_exception is not None:
        with self.assertRaises(expected_exception):
          cli_run.run(self.cli_services)
      else:
        cli_run.run(self.cli_services)

    return out, err

  def test_permissions_check_done_as_expected(self):
    testargs = []

    self.permissions_service_mock.check_required_permissions = MagicMock(
        side_effect=SilentlyExitError())

    self.run_cmd(testargs, expected_exception=SilentlyExitError)

    self.permissions_service_mock.check_required_permissions.assert_called_once(
    )

    # The permissions check should be first, and we put a side effect for it to
    # error out, so none of these methods should have been called.
    self.firebase_management_service_mock.project_get.assert_not_called()
    self.gcloud_service_mock.is_api_enabled.assert_not_called()
    self.firebase_management_service_mock.rtdb_instance_get.assert_not_called()
    self.cli_services.get_snapshot_debugger_rtdb_service.assert_not_called()
    self.debugger_rtdb_service_mock.get_schema_version.assert_not_called()

  def test_firebase_management_api_not_enabled(self):
    """Tests the situation where the Firebase Management API is not enabled.

    If this API (firebase.googleapis.com) is not enabled, that means the project
    likely has not been enabled for Firebase. The init command should emit a
    message instructing the user how to enable Firebase on their project while
    also providing the exact link to use.
    """
    testargs = []
    self.gcloud_service_mock.is_api_enabled = MagicMock(return_value=False)

    out, err = self.run_cmd(testargs, expected_exception=SilentlyExitError)

    # Verify the outputted text contains the expected migrate project
    # instructions for enabling a project for Firebase.
    self.permissions_service_mock.check_required_permissions.assert_called_once(
    )
    self.gcloud_service_mock.is_api_enabled.assert_called_once_with(
        'firebase.googleapis.com')
    self.assertIn(
        'Your Google Cloud project must be enabled for Firebase resources',
        err.getvalue())
    self.assertIn('Point your browser to the following URL:', err.getvalue())
    self.assertIn(
        'https://console.firebase.google.com/?dlAction=MigrateCloudProject'
        '&cloudProjectNumber=cli-test-project', err.getvalue())
    self.assertEqual('', out.getvalue())

    # Ensure the command exited before progressing any further
    self.firebase_management_service_mock.rtdb_instance_get.assert_not_called()
    self.cli_services.get_snapshot_debugger_rtdb_service.assert_not_called()
    self.debugger_rtdb_service_mock.get_schema_version.assert_not_called()

  def test_project_not_firebase_enabled(self):
    """Tests the situation where the project is not enabled for Firebase.

    This is the situation where the
      - Firebase Management API is enabled (firebase.googleapis.com)
      - The API was used to query the project state.
      - The response indicates the project is not enabled for Firebase

    This is a bit of a corner case situation, since if the Firebase Management
    API is enabled for the project, it would be expected that the project was
    enabled for Firebase.

    In this case the user must enable the project for Firebase, which means they
    need to follow the migration instructions that are emitted when the
    Firebase Management API is found to be disabled. However for the migration
    instructions to work the Firebase Management API must first be disabled.

    Therefore in this case the instructions emitted should be to disable the
    API, and to then rerun the init command, which will detect the API is
    disabled and emit the migration instructions.
    """
    testargs = []
    self.gcloud_service_mock.is_api_enabled = MagicMock(return_value=True)
    self.firebase_management_service_mock.project_get = MagicMock(
        return_value=FirebaseProjectGetResponse(
            status=FirebaseProjectStatus.NOT_ENABLED))

    out, err = self.run_cmd(testargs, expected_exception=SilentlyExitError)

    # Verify the outputted text contains the expected messaging about
    # disabling the API and rerunning the init command.
    # instructions for enabling a project for Firebase.
    self.permissions_service_mock.check_required_permissions.assert_called_once(
    )
    self.gcloud_service_mock.is_api_enabled.assert_called_once_with(
        'firebase.googleapis.com')
    self.firebase_management_service_mock.project_get.assert_called_once()
    self.assertIn('Your project is not yet enabled for Firebase',
                  err.getvalue())
    self.assertIn('Disable the Firebase Management API', err.getvalue())
    self.assertIn(
        'https://console.developers.google.com/apis/'
        'api/firebase.googleapis.com?project=cli-test-project', err.getvalue())
    self.assertIn('Rerun the init command', err.getvalue())
    self.assertEqual('', out.getvalue())

    # Ensure the command exited before progressing any further
    self.cli_services.get_snapshot_debugger_rtdb_service.assert_not_called()
    self.debugger_rtdb_service_mock.get_schema_version.assert_not_called()

  def test_rtdb_management_api_gets_enabled_when_not_enabled(self):
    testargs = []

    # Returns True for the first check, firebase.googleapis.com
    # Returns False for the second check, firebasedatabase.googleapis.com
    self.gcloud_service_mock.is_api_enabled = MagicMock(
        side_effect=[True, False])

    self.firebase_management_service_mock.project_get = MagicMock(
        return_value=FirebaseProjectGetResponse(
            status=FirebaseProjectStatus.ENABLED))

    self.run_cmd(testargs)

    self.gcloud_service_mock.is_api_enabled.assert_has_calls([
        call('firebase.googleapis.com'),
        call('firebasedatabase.googleapis.com')
    ])
    self.gcloud_service_mock.enable_api.assert_called_once_with(
        'firebasedatabase.googleapis.com')

  def test_rtdb_management_api_does_not_get_enabled_when_already_enabled(self):
    testargs = []

    self.gcloud_service_mock.is_api_enabled = MagicMock(return_value=True)

    self.run_cmd(testargs)

    self.gcloud_service_mock.is_api_enabled.assert_has_calls([
        call('firebase.googleapis.com'),
        call('firebasedatabase.googleapis.com')
    ])
    self.gcloud_service_mock.enable_api.assert_not_called()

  def test_use_rtdb_database_and_id_mutually_exclusive(self):
    testargs = ['--use-default-rtdb', '--database-id=foo']

    out, err = self.run_cmd(testargs, expected_exception=SystemExit)

    self.assertIn(
        'init: error: argument --database-id: not allowed '
        'with argument --use-default-rtdb', err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_db_created_when_it_doesnt_exist(self):
    # Testdata: (test_name, testargs, db_type, expected_db_name)
    # The db_type doesn't actually enter into this test, but we are setting it
    # nonetheless to the value it would have in practise.
    testcases = [
        ('Default', [], 'USER_DATABASE', 'cli-test-project-cdbg'),
        ('Use Default RTDB', ['--use-default-rtdb'], 'DEFAULT_DATABASE',
         'cli-test-project-default-rtdb'),
        ('Custom', ['--database-id=custom-database-name'], 'USER_DATABASE',
         'custom-database-name'),
    ]

    self.firebase_management_service_mock.rtdb_instance_get = MagicMock(
        return_value=DatabaseGetResponse(
            status=DatabaseGetStatus.DOES_NOT_EXIST))

    self.firebase_rtdb_service_mock.get = MagicMock(return_value=None)

    for test_name, testargs, db_type, expected_database_name in testcases:
      with self.subTest(test_name):
        self.firebase_management_service_mock.rtdb_instance_get.reset_mock()
        self.firebase_rtdb_service_mock.get.reset_mock()
        database_instance = build_database_instance(expected_database_name,
                                                    db_type)

        self.firebase_management_service_mock.rtdb_instance_create = MagicMock(
            return_value=DatabaseCreateResponse(
                status=DatabaseCreateStatus.SUCCESS,
                database_instance=database_instance))

        self.run_cmd(testargs)

        service_mock = self.firebase_management_service_mock
        service_mock.rtdb_instance_get.assert_called_once_with(
            expected_database_name)
        service_mock.rtdb_instance_create.assert_called_once_with(
            database_id=expected_database_name, location='us-central1')

        self.firebase_rtdb_service_mock.get.assert_called_once_with(
            db_path='', shallow=True, extra_retry_codes=[404])

  def test_location_specified(self):
    # Testdata: (test_name, testargs, location, db_type, expected_db_name)
    # The db_type doesn't actually enter into this test, but we are setting it
    # nonetheless to the value it would have in practise.
    #
    # By default if the user does not specify a location the CLI will default to
    # 'us-central1'. Otherwise the CLI will honour what the user specifies.
    # There is no special handling when --use-default-rtdb or --database-id are
    # used, the location is passed through as is.
    testcases = [
        # When not specified it should default to 'us-central1'
        ('Default', ['--location=us-central1'], 'USER_DATABASE',
         'cli-test-project-cdbg', 'us-central1'),
        ('Use Default RTDB', ['--use-default-rtdb', '--location=europe-west1'],
         'DEFAULT_DATABASE', 'cli-test-project-default-rtdb', 'europe-west1'),
        ('Custom',
         ['--database-id=custom-database-name', '--location=asia-southeast1'
         ], 'USER_DATABASE', 'custom-database-name', 'asia-southeast1'),
    ]

    self.firebase_management_service_mock.rtdb_instance_get = MagicMock(
        return_value=DatabaseGetResponse(
            status=DatabaseGetStatus.DOES_NOT_EXIST))

    self.firebase_rtdb_service_mock.get = MagicMock(return_value=None)

    for test_name, testargs, db_type, expected_db_name, \
        expected_location in testcases:
      with self.subTest(test_name):
        self.firebase_management_service_mock.rtdb_instance_get.reset_mock()
        self.firebase_rtdb_service_mock.get.reset_mock()
        database_instance = build_database_instance(expected_db_name, db_type)

        self.firebase_management_service_mock.rtdb_instance_create = MagicMock(
            return_value=DatabaseCreateResponse(
                status=DatabaseCreateStatus.SUCCESS,
                database_instance=database_instance))

        self.run_cmd(testargs)

        service_mock = self.firebase_management_service_mock
        service_mock.rtdb_instance_get.assert_called_once_with(expected_db_name)
        service_mock.rtdb_instance_create.assert_called_once_with(
            database_id=expected_db_name, location=expected_location)

        self.firebase_rtdb_service_mock.get.assert_called_once_with(
            db_path='', shallow=True, extra_retry_codes=[404])

  def test_handles_db_create_fails_precondition_as_expected(self):
    # Testdata: (test_name, testargs, db_type, expected_db_name)
    # The db_type doesn't actually enter into this test, but we are setting it
    # nonetheless to the value it would have in practise.
    testcases = [
        ('Default', [], 'cli-test-project-cdbg'),
        ('Use Default RTDB', ['--use-default-rtdb'],
         'cli-test-project-default-rtdb'),
        ('Custom', ['--database-id=custom-database-name'],
         'custom-database-name'),
    ]

    self.firebase_management_service_mock.rtdb_instance_get = MagicMock(
        return_value=DatabaseGetResponse(
            status=DatabaseGetStatus.DOES_NOT_EXIST))

    for test_name, testargs, expected_database_name in testcases:
      with self.subTest(test_name):
        self.firebase_management_service_mock.rtdb_instance_get.reset_mock()

        self.firebase_management_service_mock.rtdb_instance_create = MagicMock(
            return_value=DatabaseCreateResponse(
                status=DatabaseCreateStatus.FAILED_PRECONDITION))

        out, err = self.run_cmd(testargs, expected_exception=SilentlyExitError)

        service_mock = self.firebase_management_service_mock
        service_mock.rtdb_instance_get.assert_called_once_with(
            expected_database_name)
        service_mock.rtdb_instance_create.assert_called_once_with(
            database_id=expected_database_name, location='us-central1')

        project_billing_link = ('https://console.firebase.google.com/project/'
                                'cli-test-project/usage/details')

        self.assertIn(
            (f"Database '{expected_database_name}' could not be created on "
             "project 'cli-test-project'"), err.getvalue())

        self.assertIn(
            f'Please check your billing plan at {project_billing_link}',
            err.getvalue())
        self.assertIn(('Read about the billing plans at '
                       'https://firebase.google.com/pricing'), err.getvalue())
        self.assertIn(f"Visit {project_billing_link} and click 'Modify plan'",
                      err.getvalue())
        self.assertEqual('', out.getvalue())

  def test_db_already_exists_at_different_location_from_default(self):
    database_instance = build_database_instance('foo-cdbg', 'USER_DATABASE',
                                                'asia-southeast1')

    self.firebase_management_service_mock.rtdb_instance_get = MagicMock(
        return_value=DatabaseGetResponse(
            status=DatabaseGetStatus.EXISTS,
            database_instance=database_instance))

    out, err = self.run_cmd(testargs=[], expected_exception=SilentlyExitError)

    service_mock = self.firebase_management_service_mock
    service_mock.rtdb_instance_create.assert_not_called()

    self.assertIn(
        (f"the following database already exists: '{database_instance.name}', "
         "however its location 'asia-southeast1' does not match the requested "
         "location 'us-central1'"), err.getvalue())

    self.assertEqual('', out.getvalue())

  def test_db_already_exists_at_different_location_from_user_specfied(self):
    database_instance = build_database_instance('foo-cdbg', 'USER_DATABASE',
                                                'us-central1')

    self.firebase_management_service_mock.rtdb_instance_get = MagicMock(
        return_value=DatabaseGetResponse(
            status=DatabaseGetStatus.EXISTS,
            database_instance=database_instance))

    out, err = self.run_cmd(['--location=europe-west1'],
                            expected_exception=SilentlyExitError)

    service_mock = self.firebase_management_service_mock
    service_mock.rtdb_instance_create.assert_not_called()

    self.assertIn(
        (f"the following database already exists: '{database_instance.name}', "
         "however its location 'us-central1' does not match the requested "
         "location 'europe-west1'"), err.getvalue())

    self.assertEqual('', out.getvalue())

  def test_db_not_created_when_it_exists(self):
    # Testdata: (test_name, testargs, db_type, expected_db_name)
    # The db_type doesn't actually enter into this test, but we are setting it
    # nonetheless to the value it would have in practise.
    testcases = [
        ('Default', [], 'USER_DATABASE', 'cli-test-project-cdbg'),
        ('Use Default RTDB', ['--use-default-rtdb'], 'DEFAULT_DATABASE',
         'cli-test-project-default-rtdb'),
        ('Custom', ['--database-id=custom-database-name'], 'USER_DATABASE',
         'custom-database-name'),
    ]

    for test_name, testargs, db_type, expected_database_name in testcases:
      with self.subTest(test_name):
        self.firebase_management_service_mock.rtdb_instance_get.reset_mock()
        database_instance = build_database_instance(expected_database_name,
                                                    db_type)

        self.firebase_management_service_mock.rtdb_instance_get = MagicMock(
            return_value=DatabaseGetResponse(
                status=DatabaseGetStatus.EXISTS,
                database_instance=database_instance))

        self.run_cmd(testargs)

        service_mock = self.firebase_management_service_mock
        service_mock.rtdb_instance_get.assert_called_once_with(
            expected_database_name)
        service_mock.rtdb_instance_create.assert_not_called()

  def test_correct_db_url_is_used(self):
    # Testdata: (test_name, testargs, db_type, expected_db_name)
    # The db_type doesn't actually enter into this test, but we are setting it
    # nonetheless to the value it would have in practise.
    testcases = [
        ('Default', [], 'USER_DATABASE', 'cli-test-project-cdbg'),
        ('Use Default RTDB', ['--use-default-rtdb'], 'DEFAULT_DATABASE',
         'cli-test-project-default-rtdb'),
        ('Custom', ['--database-id=custom-database-name'], 'USER_DATABASE',
         'custom-database-name'),
    ]

    for test_name, testargs, db_type, expected_database_name in testcases:
      with self.subTest(test_name):
        self.cli_services.get_snapshot_debugger_rtdb_service.reset_mock()
        database_instance = build_database_instance(expected_database_name,
                                                    db_type)

        self.firebase_management_service_mock.rtdb_instance_get = MagicMock(
            return_value=DatabaseGetResponse(
                status=DatabaseGetStatus.EXISTS,
                database_instance=database_instance))

        expected_url = f'https://{expected_database_name}.firebaseio.com'
        self.assertEqual(expected_url, database_instance.database_url)

        self.run_cmd(testargs)

        get_service_mock = self.cli_services.get_snapshot_debugger_rtdb_service
        get_service_mock.assert_called_once_with(database_url=expected_url)

  def test_db_not_initialized_when_already_initialized(self):
    # By returning a value here, that indicates the database has been
    # initialized
    self.debugger_rtdb_service_mock.get_schema_version = MagicMock(
        return_value='1')

    self.run_cmd(testargs=[])

    self.debugger_rtdb_service_mock.set_schema_version.assert_not_called()

  def test_db_initialized_when_not_yet_initialized(self):
    # By returning None here, that indicates the database has not been
    # initialized
    self.debugger_rtdb_service_mock.get_schema_version = MagicMock(
        return_value=None)

    self.run_cmd(testargs=[])

    self.debugger_rtdb_service_mock.set_schema_version.assert_called_once_with(
        '1')

  def test_db_info_output_after_successful_run(self):
    database_instance = DatabaseInstance({
        'name': ('projects/1111111111/locations/us-central1/instances'
                 '/cli-test-project-cdbg'),
        'project': 'projects/1111111111',
        'databaseUrl': 'https://cli-test-project-cdbg.firebaseio.com',
        'type': 'USER_DATABASE',
        'state': 'ACTIVE'
    })

    self.firebase_management_service_mock.rtdb_instance_get = MagicMock(
        return_value=DatabaseGetResponse(
            status=DatabaseGetStatus.EXISTS,
            database_instance=database_instance))

    out, err = self.run_cmd(testargs=[])

    self.assertIn("Project 'cli-test-project' is successfully configured",
                  err.getvalue())
    self.assertIn(
        ('name:         projects/1111111111/locations/us-central1/instances/'
         'cli-test-project-cdbg'), err.getvalue())
    self.assertIn('project:      projects/1111111111', err.getvalue())
    self.assertIn('database url: https://cli-test-project-cdbg.firebaseio.com',
                  err.getvalue())
    self.assertIn('type:         USER_DATABASE', err.getvalue())
    self.assertIn('state:        ACTIVE', err.getvalue())
    self.assertEqual('', out.getvalue())
