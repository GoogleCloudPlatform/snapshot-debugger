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
"""Contains service instances and base config required by the commands.
"""

from snapshot_dbg_cli.data_formatter import DataFormatter
from snapshot_dbg_cli.exceptions import SilentlyExitError
from snapshot_dbg_cli.firebase_types import FIREBASE_RTDB_MANAGMENT_API_SERVICE
from snapshot_dbg_cli.firebase_types import DatabaseGetStatus
from snapshot_dbg_cli.firebase_types import FirebaseProject
from snapshot_dbg_cli.firebase_management_rest_service import FirebaseManagementRestService
from snapshot_dbg_cli.firebase_rtdb_rest_service import FirebaseRtdbRestService
from snapshot_dbg_cli.gcloud_cli_service import GcloudCliService
from snapshot_dbg_cli.http_service import HttpService
from snapshot_dbg_cli.permissions_rest_service import PermissionsRestService
from snapshot_dbg_cli.snapshot_debugger_rtdb_service import SnapshotDebuggerRtdbService
from snapshot_dbg_cli.snapshot_debugger_schema import SnapshotDebuggerSchema
from snapshot_dbg_cli.user_input import UserInput
from snapshot_dbg_cli.user_output import UserOutput

# The default/preferred Database ID the CLI attempts to use has this format.
SNAPSHOT_DEBUGGER_DEFAULT_DB_ID = '{project_id}-cdbg'

# All Firebase projects can have one default rtdb instance. It will have that
# following format. In some very rare cases it could be different, and the
# FirebaseProject response does contain the default instance if it exists, so
# when possible we do the right thing and get it from there, however this is
# used as a fall back when required.
FIREBASE_DEFAULT_RTDB_ID = '{project_id}-default-rtdb'

CHECK_CONFIGURATION_MSG = """
Confirm the correct project has been configured and that the 'init' command has
been run. See https://github.com/GoogleCloudPlatform/snapshot-debugger#readme
for more information.
"""


class CliServices:
  """Contains service instances and base config required by the commands.

  Attributes:
    args: The command line arguments from the CLI invocation.
    is_debug_enabled: Flag that indicates if debugging is enabled.
    data_formatter: DataFormatter instance for commands to used.
    user_input: Service for prompting and retrieving text input from the user.
    user_output: Service for emitting text output for the user.
    gcloud_service: Service for interacting with the gcloud command.
    account: The account to use, which is expected to be the user's email
      address.
    project_id: The project ID to use.
    http_service: Service for making HTTP requests.
    permissions_service: Service for checking user permissions.
    firebase_management_service: Service to use for making management/admin
      related requests to the Firebase RTDB instance.
  """

  def __init__(self, args):
    is_debug_enabled = args.debug if 'debug' in args else False

    self.args = args
    self.data_formatter = DataFormatter()
    self.user_input = UserInput()
    self.user_output = UserOutput(is_debug_enabled, self.data_formatter)
    self.gcloud_service = GcloudCliService(self.user_output)
    self.account = self.gcloud_service.config_get_account()
    self.project_id = self.gcloud_service.config_get_project()

    access_token = self.gcloud_service.get_access_token()
    self._http_service = HttpService(
        project_id=self.project_id,
        access_token=access_token,
        user_output=self.user_output)

    self.permissions_service = PermissionsRestService(
        project_id=self.project_id,
        http_service=self._http_service,
        user_output=self.user_output)

    self.firebase_management_service = FirebaseManagementRestService(
        http_service=self._http_service,
        project_id=self.project_id,
        user_output=self.user_output)

    # The services below here are deferred as they require a database url which
    # may not be known when this constructor runs.
    self._firebase_rtdb_rest_service = None
    self._debugger_rtdb_service = None

  def get_firebase_rtdb_rest_service(self, database_url):
    """Retrieve the Firebase RTDB Rest Service.

    If the database URL is not known it can be set to None, and it will be
    determined based on the cached args and the project.
    """
    if self._firebase_rtdb_rest_service is None:
      if database_url is None:
        database_url = self.get_database_url()

      self._firebase_rtdb_rest_service = FirebaseRtdbRestService(
          http_service=self._http_service,
          database_url=database_url,
          user_output=self.user_output)

    return self._firebase_rtdb_rest_service

  def get_snapshot_debugger_rtdb_service(self, database_url=None):
    """Retrieve the Snapshot Debugger RTDB Service.

    If the database URL is known it can be passed in, otherwise it will be
    be determined based on the cached args and the project.
    """
    if self._debugger_rtdb_service is None:
      self._debugger_rtdb_service = SnapshotDebuggerRtdbService(
          self.get_firebase_rtdb_rest_service(database_url),
          SnapshotDebuggerSchema(), self.user_output)

    return self._debugger_rtdb_service

  def get_snapshot_debugger_default_database_id(self):
    return SNAPSHOT_DEBUGGER_DEFAULT_DB_ID.format(project_id=self.project_id)

  def get_firebase_default_rtdb_id(self,
                                   firebase_project: FirebaseProject = None):
    """Determines the default RTDB instance ID.

    A note on terminology here, database ID, database Name and database instance
    effectively refer to the same thing. For instance, for a database with URL
    'my-project-cdbg.firebaseio.com', 'my-project-cdbg' is the id/name/instance,
    which happens to be globally unique across all firebase projects.

    Args:
      firebase_project: An instance of the current firebase project if the
        caller already has it, it can be None otherwise.

    Returns:
      The appropriate database ID for the caller to use. If the project did not
      have a default RTDB instance, None is returned.
    """
    if firebase_project is None:
      project_response = self.firebase_management_service.project_get()
      firebase_project = project_response.firebase_project

    default_rtdb = None

    if firebase_project is not None:
      default_rtdb = firebase_project.default_rtdb_instance

    if default_rtdb is None:
      default_rtdb = FIREBASE_DEFAULT_RTDB_ID.format(project_id=self.project_id)

    return default_rtdb

  def get_database_url(self):
    """Determines the database URL to use.

     The URLs for Firebase RTDBs come in two flavours:

       DATABASE_NAME.firebaseio.com for databases in us-central1
       DATABASE_NAME.REGION.firebasedatabase.app for databases in all other
         locations

    See https://firebase.google.com/docs/database/rest/start#create_a_database
    and https://firebase.google.com/docs/projects/locations#rtdb-locations for
    more information.

    Returns:
      The appropriate database URL for the caller to use.

    Raises:
      SilentlyExitError: When no database URL could be found or another unexpted
        error occurred.
    """
    if 'database_url' in self.args and self.args.database_url is not None:
      self.user_output.debug('Using user specified database '
                             f'{self.args.database_url}')
      return self.args.database_url

    if not self.gcloud_service.is_api_enabled(
        FIREBASE_RTDB_MANAGMENT_API_SERVICE):
      self.user_output.error(
          f"The '{FIREBASE_RTDB_MANAGMENT_API_SERVICE}' API service is "
          f"disabled on project '{self.project_id}'.")
      self.user_output.error(CHECK_CONFIGURATION_MSG)
      raise SilentlyExitError

    is_db_configured, db_url = self.get_database_url_from_id(
        self.get_snapshot_debugger_default_database_id())

    # If the prefered default was not found, try the defaut firebase RTDB, this
    # would be configured if '--use-default-rtdb' was used with the init
    # command.
    if not is_db_configured:
      is_db_configured, db_url = self.get_database_url_from_id(
          self.get_firebase_default_rtdb_id())

    if not is_db_configured:
      self.user_output.error('Failed to find a configured database for project '
                             f"'{self.project_id}'.")
      self.user_output.error(CHECK_CONFIGURATION_MSG)
      raise SilentlyExitError

    self.user_output.debug(f'Using configured database {db_url}')
    return db_url

  def get_database_url_from_id(self, database_id):
    """Determines the database URL based on the database_id.

    Args:
      database_id: This is the database ID whose URL we want.

    Returns:
      The appropriate database URL for the caller to use.
    """
    instance_response = self.firebase_management_service.rtdb_instance_get(
        database_id)

    if instance_response.status != DatabaseGetStatus.EXISTS:
      self.user_output.debug(f"Database ID: '{database_id}' does not exist")
      return (False, None)

    db_url = instance_response.database_instance.database_url

    rest_service = FirebaseRtdbRestService(
        http_service=self._http_service,
        database_url=db_url,
        user_output=self.user_output)

    rtdb_service = SnapshotDebuggerRtdbService(rest_service,
                                               SnapshotDebuggerSchema(),
                                               self.user_output)

    is_configured = rtdb_service.get_schema_version() is not None

    self.user_output.debug(
        f'Database ID: {database_id}, URL: {db_url}, is configured: '
        f'{is_configured}')

    return (is_configured, db_url)
