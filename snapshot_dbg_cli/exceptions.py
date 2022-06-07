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
"""Module to hold custom exceptions for the CLI.
"""


class SilentlyExitError(Exception):
  """Exception to cause the CLI to silently exit with an error.

  Should be thrown when an error occured and the code needs to exit. It's
  expected any user error messages have already been emitted. The top level
  CLI code will catch this and exit with an error without any further console
  output.
  """
  pass
