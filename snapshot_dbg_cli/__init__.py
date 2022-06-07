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
""" Snapshot Debugger CLI.

This package provides the CLI of the Snapshot Debugger.
"""

import sys

import snapshot_dbg_cli.cli_run
from snapshot_dbg_cli.exceptions import SilentlyExitError


def main():
  snapshot_dbg_cli.cli_run.run()


def run_main():
  try:
    main()
  except SilentlyExitError:
    sys.exit(1)


if __name__ == '__main__':
  run_main()
