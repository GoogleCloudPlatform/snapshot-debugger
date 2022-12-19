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
"""This module provides the current version of the package.
"""

import re
import sys

from snapshot_dbg_cli.data_formatter import DataFormatter
from snapshot_dbg_cli.exceptions import SilentlyExitError
from snapshot_dbg_cli.http_service import HttpService
from snapshot_dbg_cli.user_output import UserOutput

VERSION = 'SNAPSHOT_DEBUGGER_CLI_VERSION_0_3_0'

VERSION_PATTERN = 'SNAPSHOT_DEBUGGER_CLI_VERSION_[0-9]+_[0-9]+_[0-9]+'

VERSION_URL = ('https://raw.githubusercontent.com/GoogleCloudPlatform'
               '/snapshot-debugger/main/snapshot_dbg_cli/cli_version.py')

NEWER_VERSION_MESSAGE = """
A newer version of the CLI is available ({latest} vs {running}). To install it please run:
  $ pip install --upgrade snapshot-dbg-cli
"""


class SuppressedUserOutput(UserOutput):
  """A UserOutput subclass that prevents any user output from being emitted.
  """

  def __init__(self):
    # Just need to intialize it, the local_print override is the important bit
    # that will ensure no data is written to stdout/stderr.
    super().__init__(is_debug_enabled=False, data_formatter=DataFormatter())

  def local_print(self, *args, **kwargs):
    """Override the local_print of UserOutput to suppress all output.
    """
    pass


def extract_version_number(version_string):
  return version_string.removeprefix('SNAPSHOT_DEBUGGER_CLI_VERSION_').replace(
      '_', '.')


def running_version():
  return extract_version_number(VERSION)


def latest_version():
  # Send in SuppressedUserOutput, we don't want any error messages emitted on a
  # failure to get the version file, as it's not critical for it to succeed.
  http_service = HttpService(
      project_id=None, access_token=None, user_output=SuppressedUserOutput())
  version = None

  try:
    # Make a quick call with a low timeout, and don't care if it fails. If we
    # can't get the latest version it's not critical, we simply can't warn the
    # user if they happen to be running an older version.
    content = http_service.send_request(
        'GET', VERSION_URL, max_retries=0, timeout_sec=5)
    match = re.search(VERSION_PATTERN, content)
    if match is not None:
      version = extract_version_number(match.group(0))
  except SilentlyExitError:
    # Simply swallow the error, it is not critical to retrieve the latest, we'll
    # simply fall through and None will be returned in this case.
    pass

  return version


def check_for_newer_version():

  def version(version_string):
    return tuple(map(int, version_string.split('.')))

  running_version_string = running_version()
  latest_version_string = latest_version()

  if latest_version_string is None:
    return

  if version(latest_version_string) > version(running_version_string):
    print(
        NEWER_VERSION_MESSAGE.format(
            latest=latest_version_string, running=running_version_string),
        file=sys.stderr)
