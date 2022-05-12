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

from firebase_types import FirebaseProject
from firebase_management_rest_service import FirebaseManagementRestService
from firebase_rtdb_rest_service import FirebaseRtdbRestService
from gcloud_cli_service import GcloudCliService
from http_service import HttpService
from permissions_rest_service import PermissionsRestService
from user_input import UserInput
from user_output import UserOutput

# Unless specified otherwise, our preferred Database ID has this format.
CDBG_DEFAULT_DB_ID = '{project_id}-cdbg'

# All Firebase projects can have one default rtdb instance. It will have that
# following format. In some very rare cases it could be different, and the
# FirebaseProject response does contain the default instance if it exists, so
# when possible we do the right thing and get it from there, however this is
# used as a fall back when required.
FIREBASE_DEFAULT_RTDB_ID = '{project_id}-default-rtdb'

# The URLs for Firebase RTDBs come in two flavours:
#
# DATABASE_NAME.firebaseio.com for databases in us-central1
# DATABASE_NAME.REGION.firebasedatabase.app for databases in all other locations
#
# For now we only support the location of us-central1
DEFAULT_DB_URL = 'https://{database_id}.firebaseio.com'


class CliServices:
  """Contains service instances and base config required by the commands.

  Attributes:
    args: The command line arguments from the CLI invocation.
    is_debug_enabled: Flag that indicates if debugging is enabled.
    user_input: Service for prompting and retrieving text input from the user.
    user_output: Service for emitting text output for the user.
    gcloud_service: Service for interacting with the gcloud command.
    account: The account to use, which is expected to be the user's email
      address.
    project_id: The project ID to use.
    access_token: The access token to use in HTTP requests.
    http_service: Service for making HTTP requests.
    permissions_service: Service for checking user permissions.
    firebase_management_service: Service to use for making management/admin
      related requests to the Firebase RTDB instance.
  """

  def __init__(self, args):
    self.args = args
    is_debug_enabled = args.debug if 'debug' in args else False
    self.user_input = UserInput()
    self.user_output = UserOutput(is_debug_enabled)
    self.gcloud_service = GcloudCliService(self.user_output)
    self.account = self.gcloud_service.config_get_account()
    self.project_id = self.gcloud_service.config_get_project()
    self.access_token = self.gcloud_service.get_access_token()

    self.http_service = HttpService(
        project_id=self.project_id,
        access_token=self.access_token,
        user_output=self.user_output)

    self.permissions_service = PermissionsRestService(
        project_id=self.project_id,
        http_service=self.http_service,
        access_token=self.access_token,
        user_output=self.user_output)

    self.firebase_management_service = FirebaseManagementRestService(
        http_service=self.http_service,
        project_id=self.project_id,
        user_output=self.user_output)

    # This one is deferred as it requires a database url which may not be known
    # when this constructor runs.
    self._firebase_rtdb_service = None

  def get_firebase_rtdb_service(self, database_url=None):
    """Retrieve the Firebase RTDB Service.

    If the database URL is known it can be passed in, otherwise it will be
    be determined based on the cached args and the project.
    """

    if self._firebase_rtdb_service is None:
      if database_url is None:
        database_url = self.get_database_url(self.args)

      self._firebase_rtdb_service = FirebaseRtdbRestService(
          http_service=self.http_service,
          database_url=database_url,
          user_output=self.user_output)

    return self._firebase_rtdb_service

  def get_default_database_id(self):
    return CDBG_DEFAULT_DB_ID.format(project_id=self.project_id)

  def get_default_database_url(self):
    return DEFAULT_DB_URL.format(database_id=self.get_default_database_id())

  def get_database_id(self, args, firebase_project: FirebaseProject = None):
    """Determines the database_id based on the args and project configuration.

    A note on terminology here, database ID, database Name and database instance
    effectively refer to the same thing. For instance, for a database with URL
    'my-project-cdbg.firebaseio.com', 'my-project-cdbg' is the id/name/instance,
    which happens to be globally unique across all firebase projects.

    Args:
      args: These are the parsed command line arguments.
      firebase_project: An instance of the current firebase project if the
        caller already has it, it can be None otherwise.

    Returns:
      The appropriate database ID for the caller to use.
    """

    if 'database_id' in args and args.database_id is not None:
      return args.database_id

    if 'use_default_rtdb' in args and args.use_default_rtdb:
      if firebase_project is None:
        project_response = self.firebase_management_service.project_get()
        firebase_project = project_response.firebase_project

      default_rtdb = None

      if firebase_project is not None:
        default_rtdb = firebase_project.default_rtdb_instance

      if default_rtdb is None:
        default_rtdb = FIREBASE_DEFAULT_RTDB_ID.format(
            project_id=self.project_id)

      return default_rtdb

    return CDBG_DEFAULT_DB_ID.format(project_id=self.project_id)

  def get_database_url_from_id(self, database_id):
    """Determines the database URL based on the database_id.

    Args:
      database_id: This is the database ID whose URL we want.

    Returns:
      The appropriate database URL for the caller to use.
    """
    # Note, for now we only support the one default location, so the below
    # is fine. However this could be modified to peform an instance get call
    # that would return the URL for the database.
    return DEFAULT_DB_URL.format(database_id=database_id)

  def get_database_url(self, args):
    """Determines the database URL to use.

    Args:
      args: These are the parsed command line arguments.

    Returns:
      The appropriate database URL for the caller to use.
    """

    if 'database_url' in args and args.database_url is not None:
      return args.database_url

    database_id = self.get_database_id(args)
    return self.get_database_url_from_id(database_id)
