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
""" Unit test file for the CliServices class.
"""

import argparse
import unittest

from snapshot_dbg_cli.cli_services import CliServices
from snapshot_dbg_cli.cli_services import CHECK_CONFIGURATION_MSG
from snapshot_dbg_cli.exceptions import SilentlyExitError
from snapshot_dbg_cli.firebase_types import FirebaseProject
from snapshot_dbg_cli.firebase_types import FirebaseProjectGetResponse
from snapshot_dbg_cli.firebase_types import FirebaseProjectStatus
from snapshot_dbg_cli.firebase_types import DatabaseGetResponse
from snapshot_dbg_cli.firebase_types import DatabaseGetStatus
from snapshot_dbg_cli.firebase_types import DatabaseInstance
from unittest.mock import ANY
from unittest.mock import call
from unittest.mock import MagicMock
from unittest.mock import patch


def build_firebase_project(defaut_rtdb_name=None):
  project_data = {'resources': {}}

  if defaut_rtdb_name is not None:
    project_data['resources']['realtimeDatabaseInstance'] = defaut_rtdb_name

  return FirebaseProject(project_data)


class CliServicesTests(unittest.TestCase):
  """ Contains the unit tests for the CliServices class.
  """

  def setUp(self):
    # The following sets up Mocks for the classes that the CliServices depends
    # on/instantiates by using the patch feature of the mocking framework.
    #
    # For each dependent class we have:
    #   <class_name>_patcher
    #     Handle for the patch setup.
    #
    #   <class_name>_class_mock:
    #     The mock for the class itself. Instantiations of the class by
    #     CliServices can be checked against calls to this mock.  When the class
    #     is called to instantiate an instance, the field 'return_value' is what
    #     gets returned.  It will be Mock instance as well.
    #
    #  <class_name>_mock:
    #    This is a mock representing the actual instance of the class.

    self.data_formatter_patcher = patch(
        'snapshot_dbg_cli.cli_services.DataFormatter', autospec=True)
    self.data_formatter_class_mock = self.data_formatter_patcher.start()
    self.data_formatter_mock = self.data_formatter_class_mock.return_value
    self.addCleanup(self.data_formatter_patcher.stop)

    self.user_input_patcher = patch(
        'snapshot_dbg_cli.cli_services.UserInput', autospec=True)
    self.user_input_class_mock = self.user_input_patcher.start()
    self.user_input_mock = self.user_input_class_mock.return_value
    self.addCleanup(self.user_input_patcher.stop)

    self.user_output_patcher = patch(
        'snapshot_dbg_cli.cli_services.UserOutput', autospec=True)
    self.user_output_class_mock = self.user_output_patcher.start()
    self.user_output_mock = self.user_output_class_mock.return_value
    self.addCleanup(self.user_output_patcher.stop)

    self.gcloud_service_patcher = patch(
        'snapshot_dbg_cli.cli_services.GcloudCliService', autospec=True)
    self.gcloud_service_class_mock = self.gcloud_service_patcher.start()
    self.gcloud_service_mock = self.gcloud_service_class_mock.return_value
    self.addCleanup(self.gcloud_service_patcher.stop)

    self.http_service_mock_patcher = patch(
        'snapshot_dbg_cli.cli_services.HttpService', autospec=True)
    self.http_service_class_mock = self.http_service_mock_patcher.start()
    self.http_service_mock = self.http_service_class_mock.return_value
    self.addCleanup(self.http_service_mock_patcher.stop)

    self.permissions_service_patcher = patch(
        'snapshot_dbg_cli.cli_services.PermissionsRestService', autospec=True)
    self.permissions_service_class_mock = \
        self.permissions_service_patcher.start()
    self.permissions_service_mock = \
        self.permissions_service_class_mock.return_value
    self.addCleanup(self.permissions_service_patcher.stop)

    self.firebase_management_service_patcher = patch(
        'snapshot_dbg_cli.cli_services.FirebaseManagementRestService',
        autospec=True)
    self.firebase_management_service_class_mock = \
        self.firebase_management_service_patcher.start()
    self.firebase_management_service_mock = \
        self.firebase_management_service_class_mock.return_value
    self.addCleanup(self.firebase_management_service_patcher.stop)

    self.firebase_rtdb_service_patcher = patch(
        'snapshot_dbg_cli.cli_services.FirebaseRtdbRestService', autospec=True)
    self.firebase_rtdb_service_class_mock = \
        self.firebase_rtdb_service_patcher.start()
    self.firebase_rtdb_service_mock = \
        self.firebase_rtdb_service_class_mock.return_value
    self.addCleanup(self.firebase_rtdb_service_patcher.stop)

    self.snapshot_debugger_rtdb_service_patcher = patch(
        'snapshot_dbg_cli.cli_services.SnapshotDebuggerRtdbService',
        autospec=True)
    self.snapshot_debugger_rtdb_service_class_mock = \
        self.snapshot_debugger_rtdb_service_patcher.start()
    self.snapshot_debugger_rtdb_service_mock = \
        self.snapshot_debugger_rtdb_service_class_mock.return_value
    self.addCleanup(self.snapshot_debugger_rtdb_service_patcher.stop)

  def test_constructor_works_as_expected(self):
    """Ensure the CliServices class sets things up as expected.

    The CliServices class gathers together the required for the CLI to carry out
    the commands. It retrieves the project id, account, access token etc, and
    instantiates the required services that the commands depend on.

    Here we to ensure the expected values get installed to the public fields of
    the class. We also ensure of the services that the instances have been
    instantiated with the expected values.
    """
    args = argparse.Namespace()

    # It's expected the CliServices constructor will retrieve the configured
    # account, project_id and the user's access token via gcloud. Set up the
    # response to ensure the constructor is doing the right thing.
    # and get the user's access token for use in REST calls.
    self.gcloud_service_mock.config_get_account = MagicMock(
        return_value='foo@bar.com')
    self.gcloud_service_mock.config_get_project = MagicMock(
        return_value='cli-test-project')
    self.gcloud_service_mock.get_access_token = MagicMock(
        return_value='cli-test-access-token')

    expected_is_debug_enabled = False

    cli_services = CliServices(args)

    # Ensure the fields end up with the expected values. The commands will be
    # relying on these being set correctly.
    self.assertEqual(args, cli_services.args)
    self.assertEqual('foo@bar.com', cli_services.account)
    self.assertEqual('cli-test-project', cli_services.project_id)

    # Ensure the service fields end up populated with the expected Class
    # instances, by checking the expected <class_name>_mock instance is assigned
    # to the correct fields.
    self.assertEqual(self.data_formatter_mock, cli_services.data_formatter)
    self.assertEqual(self.user_input_mock, cli_services.user_input)
    self.assertEqual(self.user_output_mock, cli_services.user_output)
    self.assertEqual(self.gcloud_service_mock, cli_services.gcloud_service)
    self.assertEqual(self.permissions_service_mock,
                     cli_services.permissions_service)
    self.assertEqual(self.firebase_management_service_mock,
                     cli_services.firebase_management_service)

    # Ensure the service instantiations were called with the expected arguments
    # to ensure they are configured correctly.
    self.user_output_class_mock.assert_called_once_with(
        expected_is_debug_enabled, self.data_formatter_mock)

    self.gcloud_service_class_mock.assert_called_once_with(
        self.user_output_mock)

    self.http_service_class_mock.assert_called_once_with(
        project_id='cli-test-project',
        access_token='cli-test-access-token',
        user_output=self.user_output_mock)

    self.permissions_service_class_mock.assert_called_once_with(
        project_id='cli-test-project',
        http_service=self.http_service_mock,
        access_token='cli-test-access-token',
        user_output=self.user_output_mock)

    self.firebase_management_service_class_mock.assert_called_once_with(
        http_service=self.http_service_mock,
        project_id='cli-test-project',
        user_output=self.user_output_mock)

  def test_constructor_debug_works_as_expected(self):
    """Ensure the --debug CLI argument is processed correctly.

    The UserOutput class handles all the user output, and gates whether debug
    message are emitted to the user or not.  Here we ensure the CliServices
    class passes the correct is_debug_enabled value into it.
    """
    args_debug_not_set = argparse.Namespace()

    args_debug_set_false = argparse.Namespace()
    args_debug_set_false.debug = False

    args_debug_set_true = argparse.Namespace()
    args_debug_set_true.debug = True

    testcases = [
        # (Test name, args, expected is_debug_enabled)
        ('Not set', args_debug_not_set, False),
        ('Set false', args_debug_set_false, False),
        ('Set true', args_debug_set_true, True),
    ]

    for test_name, args, expected_is_debug_enabled in testcases:
      with self.subTest(test_name):
        self.user_output_class_mock.reset_mock()
        CliServices(args)

        self.user_output_class_mock.assert_called_once_with(
            expected_is_debug_enabled, ANY)

  def test_get_snapshot_debugger_rtdb_service_uses_expected_mocks(self):
    """Verifies get_snapshot_debugger_rtdb_service() used services are correct.

    This test focuses on ensuring the services created by the method are created
    correctly with the expected dependent services instances.
    """

    args = argparse.Namespace()

    service = CliServices(args).get_snapshot_debugger_rtdb_service(
        database_url='https://fake-url.firebaseio.com')

    self.assertEqual(service, self.snapshot_debugger_rtdb_service_mock)

    self.firebase_rtdb_service_class_mock.assert_called_once_with(
        http_service=self.http_service_mock,
        database_url=ANY,
        user_output=self.user_output_mock)

    self.snapshot_debugger_rtdb_service_class_mock.assert_called_once_with(
        self.firebase_rtdb_service_mock, ANY, self.user_output_mock)

  def test_get_snapshot_debugger_rtdb_service_url_provided(self):
    args = argparse.Namespace()

    service = CliServices(args).get_snapshot_debugger_rtdb_service(
        database_url='https://fake-url.firebaseio.com')

    self.assertEqual(service, self.snapshot_debugger_rtdb_service_mock)

    # Using ANY for the other parameters as the url is the focus of this test.
    self.firebase_rtdb_service_class_mock.assert_called_once_with(
        http_service=ANY,
        database_url='https://fake-url.firebaseio.com',
        user_output=ANY)

  def test_get_snapshot_debugger_rtdb_service_url_not_provided(self):
    args = argparse.Namespace()

    # Internally the code will need to call get_database_url since we are not
    # passing a url into get_snapshot_debugger_rtdb_service(). To minimize
    # extra mocking, the simplest way to specify what get_database_url() should
    # return is by using the explicit database-url cli parameter.
    args.database_url = 'https://url-from-cli-args.firebaseio.com'

    service = CliServices(args).get_snapshot_debugger_rtdb_service()

    self.assertEqual(service, self.snapshot_debugger_rtdb_service_mock)

    # Using ANY for the other parameters as the url is the focusof this test.
    self.firebase_rtdb_service_class_mock.assert_called_once_with(
        http_service=ANY,
        database_url='https://url-from-cli-args.firebaseio.com',
        user_output=ANY)

  def test_get_snapshot_debugger_rtdb_service_caching_works(self):
    args = argparse.Namespace()

    # Internally the code will need to call get_database_url since we are not
    # passing a url into get_snapshot_debugger_rtdb_service(). To minimize
    # extra mocking, the simples way to specify what get_database_url() should
    # return is by using the explicit database-url cli parameter.
    args.database_url = 'https://url-from-cli-args.firebaseio.com'

    cli_services = CliServices(args)
    service1 = cli_services.get_snapshot_debugger_rtdb_service()
    service2 = cli_services.get_snapshot_debugger_rtdb_service()

    self.assertIs(service1, service2)

    # get_snapshot_debugger_rtdb_service() was called twice, the services should
    # have only been instantiated once however, the second call should have
    # simply retrieved the cached value.
    self.firebase_rtdb_service_class_mock.assert_called_once()
    self.snapshot_debugger_rtdb_service_class_mock.assert_called_once()

  def test_get_snapshot_debugger_default_database_id(self):
    args = argparse.Namespace()
    self.gcloud_service_mock.config_get_project = MagicMock(
        return_value='cli-test-project')

    cli_services = CliServices(args)

    self.assertEqual('cli-test-project-cdbg',
                     cli_services.get_snapshot_debugger_default_database_id())

  def test_get_firebase_default_rtdb_id_project_provided(self):
    """Verifies the method does not need to retrieve the project information.

    This test verifies that by providing the get_firebase_default_rtdb_id method
    with the project instance, it makes use of it as expected and does not issue
    a firebase_management_service_mock.project_get call.
    """
    args = argparse.Namespace()
    self.gcloud_service_mock.config_get_project = MagicMock(
        return_value='cli-test-project')

    testcases = [
        # (Test Name, Provided Project Info, Expected default RTDB Name)
        ('Default RTDB In Project',
         build_firebase_project(defaut_rtdb_name='provided-rtdb-id'),
         'provided-rtdb-id'),
        ('Default RTDB Not In Project',
         build_firebase_project(defaut_rtdb_name=None),
         'cli-test-project-default-rtdb'),
    ]

    for test_name, project, expected_default_rtdb_id in testcases:
      with self.subTest(test_name):
        firebase_default_rtdb_id = CliServices(
            args).get_firebase_default_rtdb_id(project)

        self.assertEqual(expected_default_rtdb_id, firebase_default_rtdb_id)

        # Since the project was provided, it should not attempt to retrieve the
        # project information.
        self.firebase_management_service_mock.project_get.assert_not_called()

  def test_get_firebase_default_rtdb_id_project_not_provided(self):
    """Verifies the method does make a call to retrieve the project information.

    This test verifies that when the get_firebase_default_rtdb_id method is not
    called with the project information, it must make a
    firebase_management_service_mock.project_get call to retrieve it, and that
    the response is correctly used in determining the default_rtdb_id.
    """
    args = argparse.Namespace()
    self.gcloud_service_mock.config_get_project = MagicMock(
        return_value='cli-test-project')

    testcases = [
        # (Test Name, Project Get Response, Expected default RTDB Name)
        ('Project Found, RTDB Set',
         build_firebase_project(defaut_rtdb_name='found-rtdb-id'),
         'found-rtdb-id'),
        ('Project Found, RTDB Not Set',
         build_firebase_project(defaut_rtdb_name=None),
         'cli-test-project-default-rtdb'),
        ('Project Not Found', None, 'cli-test-project-default-rtdb'),
    ]

    for test_name, project, expected_default_rtdb_id in testcases:
      with self.subTest(test_name):
        status = FirebaseProjectStatus.ENABLED if project is not None \
                 else FirebaseProjectStatus.NOT_ENABLED

        project_response = FirebaseProjectGetResponse(status, project)

        # It will need to make a projct_get reques, so setup the response.
        self.firebase_management_service_mock.project_get = MagicMock(
            return_value=project_response)

        firebase_default_rtdb_id = CliServices(
            args).get_firebase_default_rtdb_id(project)

        self.assertEqual(expected_default_rtdb_id, firebase_default_rtdb_id)

  def test_get_database_url_uses_url_from_args(self):
    args = argparse.Namespace()
    args.database_url = 'https://custom.firebaseio.com'

    obtained_url = CliServices(args).get_database_url()

    self.assertEqual('https://custom.firebaseio.com', obtained_url)

  def test_get_database_url_fails_if_api_not_enabled(self):
    args = argparse.Namespace()
    self.gcloud_service_mock.config_get_project = MagicMock(
        return_value='cli-test-project')
    self.gcloud_service_mock.is_api_enabled = MagicMock(return_value=False)

    with self.assertRaises(SilentlyExitError):
      CliServices(args).get_database_url()

    self.gcloud_service_mock.is_api_enabled.assert_called_once_with(
        'firebasedatabase.googleapis.com')

    self.user_output_mock.error.assert_has_calls([
        call("The 'firebasedatabase.googleapis.com' API service is disabled on "
             "project 'cli-test-project'."),
        call(CHECK_CONFIGURATION_MSG)
    ])

  def test_get_database_url_preferred_default_exists_and_configured(self):
    args = argparse.Namespace()
    self.gcloud_service_mock.config_get_project = MagicMock(
        return_value='cli-test-project')
    self.gcloud_service_mock.is_api_enabled = MagicMock(return_value=True)

    database_instance = DatabaseInstance({
        'name': ('projects/1111111111/locations/us-central1/instances/'
                 'cli-test-project'),
        'project': 'projects/1111111111',
        'databaseUrl': 'https://cli-test-project-cdbg.firebaseio.com',
        'type': 'USER_DATABASE',
        'state': 'ACTIVE'
    })

    db_get_response = DatabaseGetResponse(DatabaseGetStatus.EXISTS,
                                          database_instance)

    self.firebase_management_service_mock.rtdb_instance_get = \
        MagicMock(return_value=db_get_response)

    self.snapshot_debugger_rtdb_service_mock.get_schema_version = \
        MagicMock(return_value='1')

    obtained_url = CliServices(args).get_database_url()
    self.assertEqual('https://cli-test-project-cdbg.firebaseio.com',
                     obtained_url)

  def test_get_database_url_must_fall_back_to_default_rtdb(self):
    args = argparse.Namespace()
    self.gcloud_service_mock.config_get_project = MagicMock(
        return_value='cli-test-project')
    self.gcloud_service_mock.is_api_enabled = MagicMock(return_value=True)

    database_instance_preferered = DatabaseInstance({
        'name': ('projects/1111111111/locations/us-central1/instances/'
                 'cli-test-project-cdbg'),
        'project': 'projects/1111111111',
        'databaseUrl': 'https://cli-test-project-cdbg.firebaseio.com',
        'type': 'USER_DATABASE',
        'state': 'ACTIVE'
    })

    database_instance_default_rtdb = DatabaseInstance({
        'name': ('projects/1111111111/locations/us-central1/instances/'
                 'cli-test-project-default-rtdb'),
        'project': 'projects/1111111111',
        'databaseUrl': 'https://cli-test-project-default-rtdb.firebaseio.com',
        'type': 'USER_DATABASE',
        'state': 'ACTIVE'
    })

    default_rtdb_response = DatabaseGetResponse(DatabaseGetStatus.EXISTS,
                                                database_instance_default_rtdb)

    testcases = [
        ('Preferred Exists But Not Configured',
         DatabaseGetResponse(DatabaseGetStatus.EXISTS,
                             database_instance_preferered), [None, '1']),
        ('Preferred Does Not Exist',
         DatabaseGetResponse(DatabaseGetStatus.DOES_NOT_EXIST), ['1']),
    ]

    for test_name, preferred_db_response, version_responses in testcases:
      with self.subTest(test_name):
        self.firebase_management_service_mock.rtdb_instance_get = \
            MagicMock(
                side_effect=[preferred_db_response, default_rtdb_response])

        self.snapshot_debugger_rtdb_service_mock.get_schema_version = \
            MagicMock(side_effect=version_responses)

        obtained_url = CliServices(args).get_database_url()

        self.assertEqual('https://cli-test-project-default-rtdb.firebaseio.com',
                         obtained_url)

  def test_get_database_url_not_found(self):
    args = argparse.Namespace()
    self.gcloud_service_mock.config_get_project = MagicMock(
        return_value='cli-test-project')
    self.gcloud_service_mock.is_api_enabled = MagicMock(return_value=True)

    default_rtdb_instance = DatabaseInstance({
        'name': ('projects/1111111111/locations/us-central1/instances/'
                 'cli-test-project-default-rtdb'),
        'project': 'projects/1111111111',
        'databaseUrl': 'https://cli-test-project-default-rtdb.firebaseio.com',
        'type': 'USER_DATABASE',
        'state': 'ACTIVE'
    })

    preferred_db_response = DatabaseGetResponse(
        DatabaseGetStatus.DOES_NOT_EXIST)

    # The version will only be queried once, for the case where the DB
    # exists, but is not configured, so this config here will suffice for the
    # sub tests.
    self.snapshot_debugger_rtdb_service_mock.get_schema_version = \
        MagicMock(return_value=None)

    testcases = [
        ('Default RTDB Exists But Not Configured',
         DatabaseGetResponse(DatabaseGetStatus.EXISTS, default_rtdb_instance)),
        ('Default RTDB Does Not Exist',
         DatabaseGetResponse(DatabaseGetStatus.DOES_NOT_EXIST)),
    ]

    for test_name, default_rtdb_response in testcases:
      with self.subTest(test_name):
        self.user_output_mock.reset_mock()

        self.firebase_management_service_mock.rtdb_instance_get = \
            MagicMock(
                side_effect=[preferred_db_response, default_rtdb_response])

        with self.assertRaises(SilentlyExitError):
          CliServices(args).get_database_url()

        self.user_output_mock.error.assert_has_calls([
            call('Failed to find a configured database for project '
                 "'cli-test-project'."),
            call(CHECK_CONFIGURATION_MSG)
        ])

  def test_get_database_url_from_id_instance_exists(self):
    args = argparse.Namespace()

    database_instance = DatabaseInstance({
        'name': ('projects/1111111111/locations/us-central1/instances/'
                 'cli-test-project-cdbg'),
        'project': 'projects/1111111111',
        'databaseUrl': 'https://fake-url.firebaseio.com',
        'type': 'USER_DATABASE',
        'state': 'ACTIVE'
    })

    db_response = DatabaseGetResponse(DatabaseGetStatus.EXISTS,
                                      database_instance)

    testcases = [
        ('Configured', '1'),
        ('Not Configured', None),
    ]

    for test_name, version in testcases:
      with self.subTest(test_name):
        self.firebase_management_service_mock.reset_mock()
        self.firebase_rtdb_service_class_mock.reset_mock()
        self.snapshot_debugger_rtdb_service_class_mock.reset_mock()
        self.user_output_mock.reset_mock()

        self.firebase_management_service_mock.rtdb_instance_get = \
            MagicMock(return_value=db_response)

        self.snapshot_debugger_rtdb_service_mock.get_schema_version = \
            MagicMock(return_value=version)

        expected_is_configured = version is not None

        obtained_is_configured, obtained_url = \
          CliServices(args).get_database_url_from_id('fake-id')

        self.assertEqual(expected_is_configured, obtained_is_configured)
        self.assertEqual('https://fake-url.firebaseio.com', obtained_url)

        rtdb_instance_get_mock = \
          self.firebase_management_service_mock.rtdb_instance_get

        rtdb_instance_get_mock.assert_called_once_with('fake-id')

        # To verify the DB instance is configured for use with the Snapshot
        # Debugger, the method will need to create temporary services to query
        # it. Here we verify these services instantiated correctly.
        self.firebase_rtdb_service_class_mock.assert_called_once_with(
            http_service=self.http_service_mock,
            database_url='https://fake-url.firebaseio.com',
            user_output=self.user_output_mock)

        self.snapshot_debugger_rtdb_service_class_mock.assert_called_once_with(
            self.firebase_rtdb_service_mock, ANY, self.user_output_mock)

  def test_get_database_url_from_id_instance_does_not_exist(self):
    args = argparse.Namespace()

    db_response = DatabaseGetResponse(DatabaseGetStatus.DOES_NOT_EXIST)

    self.firebase_management_service_mock.rtdb_instance_get = \
        MagicMock(return_value=db_response)

    obtained_is_configured, obtained_url = \
      CliServices(args).get_database_url_from_id('fake-id')

    self.assertEqual(False, obtained_is_configured)
    self.assertIsNone(obtained_url)

    rtdb_instance_get_mock = \
      self.firebase_management_service_mock.rtdb_instance_get

    rtdb_instance_get_mock.assert_called_once_with('fake-id')
