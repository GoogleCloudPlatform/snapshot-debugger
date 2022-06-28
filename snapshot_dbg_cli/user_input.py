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
"""This module provides a simple user input utility class.

This class should be used by the CLI anytime it requires user input.
"""


class UserInput:
  """This class handles prompting the user for input.

  This provides the CLI with the ability to prompt the user for input.
  """

  def prompt_user_to_continue(self):
    answer = input('Do you want to continue (Y/n)? ').lower()

    while answer and answer not in ['y', 'n']:
      answer = input("Please enter 'y' or 'n': ").lower()

    return answer != 'n'
