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
"""Service for checking user permissions.

This service is for testing if the user has IAM permissions on a project.
"""

from cli.exceptions import SilentlyExitError

TEST_IAM_PERMSSIONS_URL = "https://cloudresourcemanager.googleapis.com/v1/" \
                          "projects/{project_id}:testIamPermissions"

TEST_IAM_PERMISSIONS_PARSE_FAILURE = """
  ERROR. The testIamPermissions check did not return a dict as expected. The
  URL was:

  {url}

  The response was:

  {response}.

  The expected response format is:

  {{}} or {{ permissions: [string] }}
"""

REQUIRED_PERMISSIONS_MISSING_ERROR_MSG = """
  For the requested operation, the user is missing the following required
  permissions on project {project_id}. A user with the  Editor or Owner roles
  on a Google Cloud project would have these permissions.

  {missing_permissions}
"""


class PermissionsRestService:
  """This class implments a service for checking user permissions.

  This service allows for testing if the user has IAM permissions on a project.
  """

  def __init__(self, http_service, project_id, access_token, user_output):
    self.http_service = http_service
    self.project_id = project_id
    self.access_token = access_token
    self.user_output = user_output

  # Returns a tuple, the first field is bool which indicates if all of the
  # user has all of the requested permissions, the second field is a list of all
  # of the missing permissions.
  def test_iam_permissions(self, permissions):
    # https://cloud.google.com/resource-manager/reference/rest/v1/projects/testIamPermissions
    url = TEST_IAM_PERMSSIONS_URL.format(project_id=self.project_id)
    data = {"permissions": permissions}
    response = self.http_service.send_request("POST", url, data=data)

    if not isinstance(response, dict):
      self.user_output.error(
          TEST_IAM_PERMISSIONS_PARSE_FAILURE.format(url=url, response=response))
      raise SilentlyExitError

    active_permissions = response[
        "permissions"] if "permissions" in response else []
    missing_permissions = set(permissions).difference(set(active_permissions))

    return (not missing_permissions, missing_permissions)

  # Utility function that will print an error with the missing permissions
  # and exit if the user does not have all of the required permissions.
  def check_required_permissions(self, required_permissions):
    result = self.test_iam_permissions(required_permissions)

    if not result[0]:
      self.user_output.error(
          REQUIRED_PERMISSIONS_MISSING_ERROR_MSG.format(
              project_id=self.project_id,
              missing_permissions=result[1],
              required_permissions=required_permissions))
      raise SilentlyExitError
