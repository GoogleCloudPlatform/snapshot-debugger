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
"""Service for making management/admin related Firebase RTDB requests/queries.

This service is for making management/admin related Firebase RTDB
requests/queries using the REST interface, which is documented at
https://firebase.google.com/docs/projects/api/reference/rest/v1beta1/projects/.
"""

import json
from urllib.error import HTTPError

from snapshot_dbg_cli.firebase_types import DatabaseCreateResponse
from snapshot_dbg_cli.firebase_types import DatabaseCreateStatus
from snapshot_dbg_cli.firebase_types import DatabaseGetResponse
from snapshot_dbg_cli.firebase_types import DatabaseGetStatus
from snapshot_dbg_cli.firebase_types import DatabaseInstance
from snapshot_dbg_cli.firebase_types import FirebaseProject
from snapshot_dbg_cli.firebase_types import FirebaseProjectGetResponse
from snapshot_dbg_cli.firebase_types import FirebaseProjectStatus
from snapshot_dbg_cli.exceptions import SilentlyExitError
from snapshot_dbg_cli.http_service import print_http_error

PROJECTS_GET_URL = ("https://firebase.googleapis.com/v1beta1/projects/"
                    "{project_id}")

RTDB_INSTANCE_GET_URL = ("https://firebasedatabase.googleapis.com/v1beta/"
                         "projects/{project_id}/locations/-/instances/"
                         "{database_id}")

# There is a databaseId parameter that will be added, but is not included here
RTDB_INSTANCE_CREATE_URL = ("https://firebasedatabase.googleapis.com/v1beta/"
                            "projects/{project_id}/locations/{location}/"
                            "instances")

PROJECTS_GET_STATE_ERROR_MSG = """
  ERROR. Expected to find the 'state' field populated in the projects get
  response with a value of 'ACTIVE'. However the response was the following:

  {response}
"""

RTDB_INSTANCE_GET_STATE_ERROR_MSG = """
  ERROR. Expected to find the 'state' field populated in the database instance
  response with a value of 'ACTIVE'. However the response was the following:

  {response}
"""


class FirebaseManagementRestService:
  """Implements a service for making Firebase RTDB management REST requests.

  This service is for making management/admin related Firebase RTDB
  requests/queries using the REST interface, which is documented at
  https://firebase.google.com/docs/projects/api/reference/rest/v1beta1/projects/.
  """

  def __init__(self, http_service, project_id, user_output):
    self._http_service = http_service
    self._project_id = project_id
    self._user_output = user_output

  def project_get(self):
    """Retrieves the configured project's status.

      Returns:
        A value of type FirebaseProjectStatus representing the project's status.
    """

    # On success, a response like the following is expected:
    # {
    #   "projectId": "some-project",
    #   "projectNumber": "<numeric id>",
    #   "displayName": "jcborg-work3-test1",
    #   "name": "projects/some-project,
    #   "resources": {
    #     "hostingSite": "some-project"
    #   },
    #   "state": "ACTIVE"
    # }
    #
    # Errors (That we handle):
    #   404 NOT_FOUND: If the project has not been enabled for Firebase yet.

    # Command documentation at:
    # https://firebase.google.com/docs/projects/api/reference/rest/v1beta1/projects/get

    url = PROJECTS_GET_URL.format(project_id=self._project_id)
    request = self._http_service.build_request(
        "GET", url, include_project_header=True)
    response = None

    try:
      response = self._http_service.send(request, handle_http_error=False)
    except HTTPError as err:
      if err.code == 404:
        self._user_output.debug("Got 404, project did not exist")
        return FirebaseProjectGetResponse(
            status=FirebaseProjectStatus.NOT_ENABLED)

      print_http_error(self._user_output, request, err)
      raise SilentlyExitError from err

    if "state" not in response or response["state"] != "ACTIVE":
      # The documention doesn't specify all the values for state.
      #
      # However for the database instance command:
      # https://firebase.google.com/docs/reference/rest/database/database-management/rest/v1beta/projects.locations.instances#state
      # It lists ACTIVE, DISABLED, DELETED and LIFECYCLE_STATE_UNSPECIFIED
      #
      # For the Google Cloud Project:
      # https://cloud.google.com/resource-manager/reference/rest/v1/projects#lifecyclestate
      # it lists ACTIVE, DELETE_REQUESTED, DELETE_IN_PROGRESS and
      # LIFECYCLE_STATE_UNSPECIFIED
      #
      # Either way for our purposes we want to see 'ACTIVE', otherwise we're in
      # an unexpected state we don't handle and we will exit with an error.
      self._user_output.error(
          PROJECTS_GET_STATE_ERROR_MSG.format(response=response))
      raise SilentlyExitError

    return FirebaseProjectGetResponse(
        status=FirebaseProjectStatus.ENABLED,
        firebase_project=FirebaseProject(response))

  def rtdb_instance_get(self, database_id):
    """Checks if the database instance exists or not.

      Args:
        database_id: The database id instance to query for.

      Returns:
        A value of type DatabaseGetResponse. This will contain the status (if
        it exists or not) along with the database instance information if it
        existed.
    """

    # On success, a response like the following is expected:
    # {
    #   "name":
    # "projects/<numeric id>/locations/us-central1/instances/some-projet-cdbg",
    #   "project": "projects/<numeric id>",
    #   "databaseUrl": "https://some-project-cdbg.firebaseio.com",
    #   "type": "USER_DATABASE",
    #   "state": "ACTIVE"
    # }
    #
    # Errors:
    #   404 NOT_FOUND: If the database instance does not exist.
    #
    # Command documentation at:
    # https://firebase.google.com/docs/reference/rest/database/database-management/rest/v1beta/projects.locations.instances/get
    try:
      url = RTDB_INSTANCE_GET_URL.format(
          project_id=self._project_id, database_id=database_id)
      request = self._http_service.build_request(
          "GET", url, include_project_header=True)

      response = self._http_service.send(request, handle_http_error=False)
      database_instance = DatabaseInstance(response)

      # The documention specifies the following values for state
      # ACTIVE, DISABLED, DELETED and LIFECYCLE_STATE_UNSPECIFIED
      #
      # For our purposes we want to see 'ACTIVE', otherwise we're in an
      # unexpected state we don't handle and we will exit with an error.
      if database_instance.state != "ACTIVE":
        self._user_output.error(
            RTDB_INSTANCE_GET_STATE_ERROR_MSG.format(response=response))
        raise SilentlyExitError

      return DatabaseGetResponse(
          status=DatabaseGetStatus.EXISTS, database_instance=database_instance)
    except HTTPError as err:
      if err.code == 404:
        print_http_error(self._user_output, request, err, is_debug_message=True)
        self._user_output.debug("Got 404, DB did not exist")
        return DatabaseGetResponse(status=DatabaseGetStatus.DOES_NOT_EXIST)

      print_http_error(self._user_output, request, err)
      raise SilentlyExitError from err
    except ValueError as e:
      self._user_output.error(e.args)
      raise SilentlyExitError from e

  def rtdb_instance_create(self, database_id, location):
    """Creates the database instance.

      Returns:
        A value of type DatabaseCreateResponse. This will contain the status
        of the create call, along with the database instance information if it
        succeeded.
    """

    # On success, a response like the following is expected:
    # {
    #   "name":
    # "projects/<numeric id>/locations/us-central1/instances/some-projet-cdbg",
    #   "project": "projects/<numeric id>",
    #   "databaseUrl": "https://some-project-cdbg.firebaseio.com",
    #   "type": "USER_DATABASE",
    #   "state": "ACTIVE"
    # }
    #
    # Errors:
    # One reason his can happen if you're on the spark plan, you need to be on
    # the blaze plan to be able to create a USER_DATABASE
    # {
    #   "error": {
    #     "code": 400,
    #     "message": "Precondition check failed.",
    #     "status": "FAILED_PRECONDITION"
    #   }
    # }
    #
    # Command documentation at:
    # https://firebase.google.com/docs/reference/rest/database/database-management/rest/v1beta/projects.locations.instances/create
    #
    # NOTE: There is the possibility when using DEFAULT_DATABASE (though very
    # unlikely) that the standard default rtdb name isn't available and the
    # backend will suggest one that will work. In this case the response
    # would look like the following:
    #
    # "error": {
    #   "code": 400,
    #   "status": "INVALID_ARGUMENT",
    #    "details": [
    #      {
    #        "@type": "type.googleapis.com/google.rpc.ErrorInfo",
    #        "reason": "INVALID",
    #        "metadata": {
    #         "suggested_database_ids": "jcborg-work3-test1-default-rtdb"
    #        }
    #      }
    #    ]
    #  }
    #
    # Currently we simply fail out on this case.

    try:
      url = RTDB_INSTANCE_CREATE_URL.format(
          project_id=self._project_id, location=location)
      parameters = [f"databaseId={database_id}"]

      use_default_db = database_id.endswith("-default-rtdb")
      data = {"type": "DEFAULT_DATABASE" if use_default_db else "USER_DATABASE"}

      request = self._http_service.build_request(
          "POST",
          url,
          include_project_header=True,
          parameters=parameters,
          data=data)

      response = self._http_service.send(
          request, max_retries=0, handle_http_error=False)

      database_instance = DatabaseInstance(response)

      return DatabaseCreateResponse(
          status=DatabaseCreateStatus.SUCCESS,
          database_instance=database_instance)
    except HTTPError as err:
      error_message = err.read().decode()

      if err.code == 400:
        try:
          parsed_error = json.loads(error_message)
          if parsed_error["error"]["status"] == "FAILED_PRECONDITION":
            self._user_output.debug("Got 400:", parsed_error)
            return DatabaseCreateResponse(
                DatabaseCreateStatus.FAILED_PRECONDITION)
        except (TypeError, KeyError, ValueError):
          pass

      print_http_error(
          self._user_output, request, err, error_message=error_message)
      raise SilentlyExitError from err
    except ValueError as e:
      self._user_output.error(e.args)
      raise SilentlyExitError from e
