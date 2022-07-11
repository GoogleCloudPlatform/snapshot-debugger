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
"""This module provides a service for calling gcloud.

This can be used to use the gcloud command under the covers to retrieve things
such as the gcloud configured project, account, get the users access token etc.
"""

import json
import subprocess

from snapshot_dbg_cli.exceptions import SilentlyExitError

# As a general note, error messages out of gcloud are detailed. So when a gcloud
# command fails we are sure to output the error message, as the messsage below
# show. Eg, when there is no logged in account set, the gcloud error message is
# the following:
#
# ERROR: (gcloud.auth.print-access-token) You do not currently have an active
# account selected.
# Please run:
#
#   $ gcloud auth login
#
# to obtain new credentials.
#
# If you have already logged in with a different account:
#
#     $ gcloud config set account ACCOUNT
#
# to select an already authenticated account to use.
#

GCLOUD_CMD_NOT_FOUND_ERROR_MSG = """
A file not found error occured attempting to run the 'gcloud' cli command. Please
ensure gcloud is installed and that the command is in the PATH and then try again.
"""

GCLOUD_OS_ERROR_MSG = """
The following error occured attempting to run the 'gcloud' cli command:

{err}
"""

UNEXPECTED_ERROR_MSG = """
The following unexpected error occured attempting to run the 'gcloud' cli command:

{err}
"""

GCLOUD_COMMAND_FAILED_MSG = """
Command '{command}' failed.

stdout: {stdout}
stderr: {stderr}
"""

PARSE_GCLOUD_OUTPUT_AS_JSON_FAILED_MSG = """
Failure occured parsing gcloud output as json.

Command: '{command}'
Data To Parse: '{gcloud_output}'
"""

PARSE_CONFIGURED_ACCOUNT_ERROR_MSG = """
An error occured attempting to parse the account obtained from gcloud'.

Gcloud output: {gcloud_output}

However the expected format was expected to be: "<account>"
"""

PARSE_CONFIGURED_PROJECT_ERROR_MSG = """
An error occured attempting to parse the project ID obtained from gcloud'.

Gcloud output: {gcloud_output}

However the expected format was expected to be: "<account>"
"""

PARSE_ACCESS_TOKEN_ERROR_MSG = """
An error occured attempting to parse the access token obtained from gcloud.

Gcloud output: {gcloud_output}

However the expected format was expected to be:

{{
  "token": "<ACCESS_TOKEN>"
}}
"""

PARSE_SERVICES_ERROR_MSG = """
An error occured attempting to parse the gcloud services output from gcloud.'.

Gcloud output: {gcloud_output}

However the expected format was expected to be:

# If the API service was not enabled:
[]

# If the API service was enabled, it should contain one entry with this
# subset of data:
[
  {{
    "config": {{
      [...snip]
      "name": "{api_name}",
    }}
  [...snip]
  }}
]
"""


class GcloudCliService:
  """This class implements a service for calling the gcloud CLI.

  This can be used to use the gcloud command under the covers to retrieve things
  such as the gcloud configured project, account, get the users access token
  etc.
  """

  def __init__(self, user_output):
    self._user_output = user_output

  def config_get_account(self):
    account = self.run(["config", "get-value", "account"])

    # This is a sanity check, if the command succeeded and the json parsing
    # passed, we should have non zero length string.
    if not isinstance(account, str) or not account:
      self._user_output.error(
          PARSE_CONFIGURED_ACCOUNT_ERROR_MSG.format(gcloud_output=account))
      raise SilentlyExitError

    return account

  def config_get_project(self):
    project_id = self.run(["config", "get-value", "project"])

    # This is a sanity check, if the command succeeded and the json parsing
    # passed, we should have non zero length string.
    if not isinstance(project_id, str) or not project_id:
      self._user_output.error(
          PARSE_CONFIGURED_PROJECT_ERROR_MSG.format(gcloud_output=project_id))
      raise SilentlyExitError

    return project_id

  def get_access_token(self):
    gcloud_output = self.run(["auth", "print-access-token"])

    token = gcloud_output.get("token", None) \
              if isinstance(gcloud_output, dict) else None

    if not token:
      self._user_output.error(
          PARSE_ACCESS_TOKEN_ERROR_MSG.format(gcloud_output=gcloud_output))
      raise SilentlyExitError

    return token

  def is_api_enabled(self, api_name):
    services_response = self.run(
        ["services", "list", "--enabled", f"--filter=config.name={api_name}"])

    if not isinstance(services_response, list):
      self._user_output.error(
          PARSE_SERVICES_ERROR_MSG.format(
              gcloud_output=services_response, api_name=api_name))
      raise SilentlyExitError

    # If there were no results, an empty array would be returned, and in this
    # case an empty array indicates it wasn't enabled.
    return len(services_response) >= 1

  def enable_api(self, api_name):
    self.run(["services", "enable", api_name])

  def run(self, gcloud_arguments):
    command_array = ["gcloud"] + gcloud_arguments + ["--format=json"]
    result = None

    try:
      self._user_output.debug(f"Running command: '{' '.join(command_array)}'")

      # Notes:
      #   - The 'stdout/stderr' arguments are used here instead of
      #     'capture_ouput', as it was added in Python 3.7 and this CLI is
      #     attempting to maintain compatibility with Python 3.6.
      #   - The 'universal_newlines' argument is used to turn on text mode for
      #     the captured stdout/stderr data. This is used instead of 'text' to
      #     be compatible with Python 3.6, as 'text' was added in 3.7
      #   - check=False ensures on failure no exception is thrown, callers will
      #     need to check the 'returncode' on the result.
      result = subprocess.run(
          command_array,
          stdout=subprocess.PIPE,
          stderr=subprocess.PIPE,
          universal_newlines=True,
          check=False)
    except FileNotFoundError as err:
      self._user_output.error(GCLOUD_CMD_NOT_FOUND_ERROR_MSG)
      raise SilentlyExitError from err
    except OSError as err:
      self._user_output.error(GCLOUD_OS_ERROR_MSG.format(err=err))
      raise SilentlyExitError from err
    # SubprocessError is used as base class for most exceptions in the
    # subprocess module. ValueError can also be raised if Popen is called with
    # invalid arguments, though that would be a programing error and should only
    # happen at dev time. We explicitly list SubproccessError here, and use
    # Exception as a blanket catch all, these are all unexpected errors.
    except (subprocess.SubprocessError, Exception) as err:
      self._user_output.error(UNEXPECTED_ERROR_MSG.format(err=err))
      raise SilentlyExitError from err

    if result.returncode != 0:
      self._user_output.error(
          GCLOUD_COMMAND_FAILED_MSG.format(
              command=" ".join(command_array),
              stdout=result.stdout,
              stderr=result.stderr))
      raise SilentlyExitError

    self._user_output.debug("Result:", result)

    try:
      return json.loads(result.stdout)
    except json.JSONDecodeError as err:
      self._user_output.error(
          PARSE_GCLOUD_OUTPUT_AS_JSON_FAILED_MSG.format(
              command=" ".join(command_array), gcloud_output=result.stdout),
          err)
      raise SilentlyExitError from err
