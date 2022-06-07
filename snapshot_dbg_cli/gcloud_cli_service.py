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

CONFIG_GET_ACCOUNT_ERROR_MSG = """
An error occured attempting to retrieve the currently configured account using
gcloud command '{cmd}'. To note, this CLI relies on the gcloud command and
requires that there is configured account. The error message from gcloud is:

{err}
"""

PARSE_CONFIGURED_ACCOUNT_ERROR_MSG = """
An error occured attempting to parse the response from gcloud command '{cmd}'.

The error was:

{err}

The response was

{response}

However the expected format was expected to be:

"<account>"
"""

CONFIG_GET_PROJECT_ERROR_MSG = """
An error occured attempting to retrieve the currently configured project using
gcloud command '{cmd}'. To note, this CLI relies on the gcloud command and
requires that there is configured project. The error message from gcloud is:

{err}
"""

PARSE_CONFIGURED_PROJECT_ERROR_MSG = """
An error occured attempting to parse the response from gcloud command '{cmd}'.

The error was:

{err}

The response was

{response}

However the expected format was expected to be:

"<project_id>"
"""

PRINT_ACCESS_TOKEN_ERROR = """
An error occured attempting to retrieve the current account's access token using
gcloud command '{cmd}'. To note, this CLI relies on the gcloud command and
requires that there is an active login session. The error message from gcloud
is:

{err}
"""

PARSE_ACCESS_TOKEN_ERROR = """
An error occured attempting to parse the response from gcloud command '{cmd}'.

The error was:

{err}

The response was

{response}

However the expected format was expected to be:

{{
  "token": "<ACCESS_TOKEN>"
}}
"""

API_ENABLED_CHECK_ERROR = """
An error occurred attempting to check if API '{api_name}' is enabled using
gcloud command '{cmd}'.  The error message from gcloud is:

{err}
"""

ENABLE_API_ERROR = """
An error occurred attempting to check if the Firebase Management API is enabled
using gcloud command '{cmd}'.  The error message from gcloud is:

{err}
"""

PARSE_SERVICES_ERROR = """
An error occured attempting to parse the response from gcloud command '{cmd}'.

The error was:

{err}

The response was:

{response}

However the expected format was expected to be:

# If the API service was enabled:
[]

# If the API service was not enabled, it should contain one entry with this
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
    self.user_output = user_output

  def config_get_account(self):
    command = ["config", "get-value", "account", "--format=json"]

    result = self.run(command)

    if result.returncode != 0:
      self.user_output.error(
          CONFIG_GET_ACCOUNT_ERROR_MSG.format(
              cmd=result.args, err=result.stderr))
      raise SilentlyExitError

    account = None

    try:
      account = json.loads(result.stdout)

      # This is a sanity check, if the command succeeded and the json parsing
      # passed, we should have non zero length string.
      if not isinstance(account, str) or not account:
        raise Exception

    except Exception as err:
      # We just do a blanket exception catch. We specified format=json in the
      # gcloud command, so valid json should have been returned and the command
      # should have returned it as an array. So any failure is an unexpected
      # exception.
      self.user_output.error(
          PARSE_CONFIGURED_ACCOUNT_ERROR_MSG.format(
              err=err, cmd=result.args, response=result.stdout))
      raise SilentlyExitError from err

    return account

  def config_get_project(self):
    command = ["config", "get-value", "project", "--format=json"]

    result = self.run(command)

    if result.returncode != 0:
      self.user_output.error(
          CONFIG_GET_PROJECT_ERROR_MSG.format(
              cmd=result.args, err=result.stderr))
      raise SilentlyExitError

    project_id = None

    try:
      project_id = json.loads(result.stdout)

      # This is a sanity check, if the command succeeded and the json parsing
      # passed, we should have non zero length string.
      if not isinstance(project_id, str) or not project_id:
        raise Exception

    except Exception as err:
      # We just do a blanket exception catch. We specified format=json in the
      # gcloud command, so valid json should have been returned and the command
      # should have returned it as an array. So any failure is an unexpected
      # exception.
      self.user_output.error(
          PARSE_CONFIGURED_PROJECT_ERROR_MSG.format(
              err=err, cmd=result.args, response=result.stdout))
      raise SilentlyExitError from err

    return project_id

  def is_api_enabled(self, api_name):
    command = [
        "services", "list", "--enabled", "--format=json",
        f"--filter=config.name={api_name}"
    ]

    result = self.run(command)

    if result.returncode != 0:
      self.user_output.error(
          API_ENABLED_CHECK_ERROR.format(
              api_name=api_name, cmd=result.args, err=result.stderr))
      raise SilentlyExitError

    is_enabled = False

    try:
      # If there were no results, an empty array would be returned.
      is_enabled = len(json.loads(result.stdout)) >= 1

    except Exception as err:
      # We just do a blanket exception catch. We specified format=json in the
      # gcloud command, so valid json should have been returned and the command
      # should have returned it as an array. So any failure is an unexpected
      # exception.
      self.user_output.error(
          PARSE_SERVICES_ERROR.format(
              err=err,
              cmd=result.args,
              response=result.stdout,
              api_name=api_name))
      raise SilentlyExitError from err

    return is_enabled

  def enable_api(self, api_name):
    command = ["services", "enable", api_name]

    result = self.run(command)

    if result.returncode != 0:
      self.user_output.error(
          ENABLE_API_ERROR.format(
              api_name=api_name, cmd=result.args, err=result.stderr))
      raise SilentlyExitError

  def get_access_token(self):
    command = ["auth", "print-access-token", "--format=json"]
    result = self.run(command)

    if result.returncode != 0:
      self.user_output.error(
          PRINT_ACCESS_TOKEN_ERROR.format(cmd=result.args, err=result.stderr))
      raise SilentlyExitError

    access_token = None

    try:
      access_token = json.loads(result.stdout)["token"]

    except Exception as err:
      # We just do a blanket exception catch. We specified format=json in the
      # gcloud command, so valid json and is should parse to a dict with a key
      # of 'token' So any failure in the try is an unexpected exception.
      self.user_output.error(
          PARSE_ACCESS_TOKEN_ERROR.format(
              err=err, cmd=result.args, response=result.stdout))
      raise SilentlyExitError from err

    return access_token

  def run(self, command):
    command_array = ["gcloud"] + command

    try:
      self.user_output.debug(f"Running command: '{' '.join(command_array)}'")

      # Note, the stdout/stderr arguments are used here instead of
      # 'capture_ouput', as it was added in Python 3.7 and this CLI
      # is attempting to maintain compatibility with Python 3.6.
      result = subprocess.run(
          command_array,
          stdout=subprocess.PIPE,
          stderr=subprocess.PIPE,
          universal_newlines=True,
          check=False)
      self.user_output.debug("Result:", result)
      return result
    except FileNotFoundError as err:
      self.user_output.error(GCLOUD_CMD_NOT_FOUND_ERROR_MSG)
      raise SilentlyExitError from err
    except OSError as err:
      self.user_output.error(GCLOUD_OS_ERROR_MSG.format(err=err))
      raise SilentlyExitError from err
    except BaseException as err:
      self.user_output.error(UNEXPECTED_ERROR_MSG.format(err=err))
      raise SilentlyExitError from err
