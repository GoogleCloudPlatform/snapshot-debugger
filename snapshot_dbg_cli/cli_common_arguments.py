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
"""Contains some common cli arguments.

The arguments contained here are needed by 2 or more cli commands, and so are
grouped here so they can be reused.
"""

import argparse
import os

from enum import Enum

DATABASE_URL_ENV_VAR_NAME = 'SNAPSHOT_DEBUGGER_DATABASE_URL'
DEBUGGEE_ID_ENV_VAR_NAME = 'SNAPSHOT_DEBUGGER_DEBUGGEE_ID'


class OutputFormat(Enum):
  """ Enum that represents the type of the user output to use for the command.
  """

  # Indicates default human readable output should be used.
  DEFAULT = 1

  # Indicates JSON output is desired. No special formatting will be used and so
  # this format is simply  meant to be machine readable.
  JSON = 2

  # Indicates JSON output is desired, but that pretty printing should be used.
  PRETTY_JSON = 3

  def is_a_json_value(self):
    return self in [self.JSON, self.PRETTY_JSON]

  def is_pretty_json(self):
    return self is self.PRETTY_JSON

  @staticmethod
  def parse_arg(format_arg):
    mappings = {
        'default': OutputFormat.DEFAULT,
        'json': OutputFormat.JSON,
        'pretty-json': OutputFormat.PRETTY_JSON
    }
    enum_val = mappings.get(format_arg, None)

    if enum_val is None:
      raise argparse.ArgumentTypeError(
          f'Invalid format argument provided: {format_arg}')

    return enum_val


DATABASE_URL_HELP = f"""
Specify the database URL for the CLI to use. This should only be used as an
override to make the CLI talk to a specific instance and isn't expected to be
needed. It is only required if the '--database-id' argument was used with the
init command.  This value may be specified either via this command line argument
or via the '{DATABASE_URL_ENV_VAR_NAME}' environment variable.  When both
are specified, the value from the command line takes precedence.
"""

FORMAT_HELP = """
Set the format for printing command output resources. The default is a
command-specific human-friendly output format. The supported formats are:
  default, json (raw) and pretty-json (formatted json).
"""

DEBUG_HELP = 'Enable CLI debug messages.'

DEBUGGEE_ID_HELP = f"""
Specify the debuggee ID. It must be an ID obtained from the list_debuggees
command. This value is required, it must be specified either via this command
line argument or via the '{DEBUGGEE_ID_ENV_VAR_NAME}' environment variable.
When both are specified, the value from the command line takes precedence.
"""


class CommonArgumentParsers:
  """Common cli arguments for commands to use.

  The common command arguments are grouped here so commands can reuse them.
  The arguments here are expected to be needed by 2 or more commands.

  Attributes:
    database_url: Argument parser for the 'database-url' cli argument.
    format: Argument parser for the 'format' cli argument.
    debuggee_id: Argument parser for the 'debuggee-id' cli argument.
  """

  def __init__(self):
    self.database_url = self.create_database_url_parser()
    self.format = self.create_format_parser()
    self.debuggee_id = self.create_debuggee_id_parser()

  @staticmethod
  def create_database_url_parser():
    arguments = {
        'help': DATABASE_URL_HELP,
    }

    env_database_url = os.environ.get(DATABASE_URL_ENV_VAR_NAME)

    if env_database_url is not None:
      arguments['default'] = env_database_url

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--database-url', **arguments)
    return parser

  @staticmethod
  def create_format_parser():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        '--format',
        help=FORMAT_HELP,
        default='default',
        type=OutputFormat.parse_arg)
    return parser

  @staticmethod
  def create_debuggee_id_parser():
    arguments = {
        'help': DEBUGGEE_ID_HELP,
    }

    env_debuggee_id = os.environ.get(DEBUGGEE_ID_ENV_VAR_NAME)

    if env_debuggee_id is not None:
      arguments['default'] = env_debuggee_id
    else:
      arguments['required'] = True

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--debuggee-id', **arguments)
    return parser


class RequiredArgumentParsers:
  """Required cli arguments all commands must use.

  The required command arguments are grouped here so commands can reuse them.
  The arguments here are required to be used by all commands.

  Attributes:
    parsers: List of all required argument parsers.
  """

  def __init__(self):
    self.parsers = [self.create_debug_parser()]

  @staticmethod
  def create_debug_parser():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--debug', help=DEBUG_HELP, action='store_true')
    return parser
