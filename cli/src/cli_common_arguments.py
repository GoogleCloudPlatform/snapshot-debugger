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

DATABASE_URL_HELP = """
Specify the database URL for the CLI to use. This should only be used as an
override to make the CLI talk to a specific instance and isn't expected to be
needed. If you are on the Spark plan and want the CLI to use the default
instance use the --use-default-rtdb flag instead. If neither of the
--database-id or --use-default-rtdb flags are used with the init command, the
CLI uses the default url.
"""

FORMAT_HELP = """
Set the format for printing command output resources. The default is a
command-specific human-friendly output format. The supported formats are:
  default, json (raw) and pretty-json (formatted json).
"""

DEBUG_HELP = 'Enable CLI debug messages.'

USE_DEFAULT_RTDB_HELP = """
Required for projects on the Spark plan. When specified, instructs the CLI to
use the project's default Firebase RTDB database.
"""

DEBUGGEE_ID_HELP = """
Specify the debuggee ID. It must be an ID obtained from the list_debuggees
command.
"""


class CommonArgumentParsers:
  """Common cli arguments for commands to use.

  The common command arguments are grouped here so commands can reuse them.
  The arguments here are expected to be needed by 2 or more commands.

  Attributes:
    database_url: Argument parser for the 'database-url' cli argument.
    format: Argument parser for the 'format' cli argument.
    use_default_rtdb: Argument parser for the 'use-default-rtdb' cli argument.
    debuggee_id: Argument parser for the 'debuggee-id' cli argument.
  """

  def __init__(self):
    self.database_url = self.create_database_url_parser()
    self.format = self.create_format_parser()
    self.use_default_rtdb = self.create_use_default_rtdb_parser()
    self.debuggee_id = self.create_debuggee_id_parser()

  @staticmethod
  def create_database_url_parser():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--database-url', help=DATABASE_URL_HELP)
    return parser

  @staticmethod
  def create_format_parser():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--format', help=FORMAT_HELP, default='default')
    return parser

  @staticmethod
  def create_use_default_rtdb_parser():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        '--use-default-rtdb', help=USE_DEFAULT_RTDB_HELP, action='store_true')
    return parser

  @staticmethod
  def create_debuggee_id_parser():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        'debuggee_id', metavar='debuggee-id', help=DEBUGGEE_ID_HELP)
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
