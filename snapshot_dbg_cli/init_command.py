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
"""This module contains the support for the init command.

The init command is used to initialize a GCP project with the required Firebase
resources so Snapshot Debugger can use Firebase as a backend.
"""

from snapshot_dbg_cli.firebase_types import FIREBASE_MANAGMENT_API_SERVICE
from snapshot_dbg_cli.firebase_types import FIREBASE_RTDB_MANAGMENT_API_SERVICE
from snapshot_dbg_cli.firebase_types import DatabaseCreateStatus
from snapshot_dbg_cli.firebase_types import DatabaseGetStatus
from snapshot_dbg_cli.firebase_types import FirebaseProjectStatus
from snapshot_dbg_cli.exceptions import SilentlyExitError
from snapshot_dbg_cli.cli_services import SNAPSHOT_DEBUGGER_DEFAULT_DB_ID

DATABASE_ID_HELP = """
Specify the ID of the database instance for the CLI to create as part of the
initialization process. If not specified, defaults to '{default_database_id}'.
"""

CMD_DESCRIPTION = """
Initializes a GCP project with the required Firebase resources so Snapshot
Debugger can use Firebase as a backend. This must be done at least once per
project. This command is safe to run multiple times, as the command will
determine what, if anything, needs to be done. Some steps require the user to
perform a requested action and then rerun the command to make progress.
"""

DEFAULT_LOCATION = 'us-central1'

LOCATION_HELP = f"""
Location for the database instance, defaults to {DEFAULT_LOCATION}
"""

USE_DEFAULT_RTDB_HELP = """
Required for projects on the Spark plan. When specified, instructs the CLI to
use the project's default Firebase RTDB database.
"""

FIREBASE_CONSOLE_URL = ('https://console.firebase.google.com/project/'
                        '{project_id}')

MIGRATE_PROJECT_URL = ('https://console.firebase.google.com/'
                       '?dlAction=MigrateCloudProject&cloudProjectNumber='
                       '{project_id}')

FIREBASE_BILLING_URL = 'https://firebase.google.com/pricing'

FIREBASE_MANAGEMENT_API_URL = (
    'https://console.developers.google.com/apis/'
    'api/firebase.googleapis.com?project={project_id}')

ENABLE_FIREBASE_API_GCLOUD_CMD = """
gcloud services enable firebase.googleapis.com
"""

BILLING_PLAN_URL = ('https://console.firebase.google.com/project/{project_id}/'
                    'usage/details')

CONSOLE_RTDB_URL = ('https://console.firebase.google.com/project/{project_id}/'
                    'database')

# These permissions are all required in order to carry out the 'init' tasks.
# The Editor or Owner of a Google Cloud project will have these permissions.
REQUIRED_PERMISSIONS = [
    'firebase.projects.create', 'firebase.projects.update',
    'firebasedatabase.instances.create', 'firebasedatabase.instances.get',
    'resourcemanager.projects.get', 'serviceusage.services.enable',
    'serviceusage.services.get'
]

MIGRATE_PROJECT_INSTRUCTIONS = """
Your Google Cloud project must be enabled for Firebase resources. To do so,
complete the following steps and then run the init command again.

1. Enable your Google Cloud project for Firebase resources.

  a. Point your browser to the following URL:
     {migration_link}

  b. Select your Project ID, which is auto populated in the 'Project name'
     field, then click 'Continue'.

     If your project name was not auto populated:

       i. Check if your Google Cloud project has already been enabled for
          Firebase by checking for it here at the URL below, if found skip to
          step 2:

          {firebase_console_link}

       ii. Verify you have selected the correct Google Cloud project and
           then run the 'init' command again.

  c. If your Google Cloud project has billing enabled you'll be prompted to
     confirm the Firebase billing plan, 'Blaze Pay as you go'. Click 'Confirm
     plan'.

      NOTE: The Debugger will be using the Firebase RTDB service. It's expected
            the usage will be low enough to fit in the free usage limits
            specified at {firebase_billing_link}.

  d. Read the 'Few things to remember when adding Firebase to a Google Cloud
     project' and then click 'Continue'.

  e. (Optional) Enable Google Analytics. For Debugger use this is not required
     and you can deselect the option.  If however you choose to enable Google
     Analytics, follow the prompts to select or create a Google Analytics
     account.

  e. Click 'Add Firebase'.

2. Enable the Firebase Management API if required:

  a. Point your web browser to the following link:
     {firebase_api_link}

  b. If the Firebase Management API is not reported as 'API Enabled', click
     'ENABLE' to enable the API. If the Firebase Management API is already
     enabled, go to step 3.

3. Run the init command again to determine the next required steps.
"""

DISABLE_FIREBASE_API_MESSAGE = """
Your project is not yet enabled for Firebase, however the Firebase Management
API is enabled. Before proceeding you'll need to do the following:

1. Disable the Firebase Management API

  Go to the link below and click 'DISABLE API'

  {firebase_api_link}

2. Rerun the init command.
"""

CHECK_BILLING_PLAN_MESSAGE = """
Database '{database_id}' could not be created on project '{project_id}'. One
potential reason for this failure is that the project is on the Spark billing
plan. When using the Spark plan, the '--use-default-rtdb' flag must be passed
with the init command.

Please check your billing plan at {project_billing_plan_link}

If the Spark billing plan is in use, there are two options:

  Option 1. Stay on the Spark plan and have the Snapshot Debugger use the
            project's default database.

    a. Rerun the init command with the '--use-default-rtdb' flag.

    b. The '--use-default-rtdb' flag must be passed with all CLI commands.

  Option 2. Upgrade to the Blaze billing plan.

    The Snapshot Debugger uses the Firebase RTDB service. It's expected the
    usage will be low enough to fit in the free usage limits specified at
    {firebase_billing_link}.

    a. Read about the billing plans at {firebase_billing_link}.

    b. Visit {modify_billing_plan_link} and click 'Modify plan'.

    c. Rerun the init command.
"""

INIT_COMPLETE_MSG = """
Project '{project_id}' is successfully configured with the Firebase Realtime
Database for use by Snapshot Debugger.

The full database information is below. If you have specified a custom database
ID the url below is the one you'll need to specify when using the other cli
commands.

  name:         {db_name}
  project:      {db_project}
  database url: {db_url}
  type:         {db_type}
  state:        {db_state}
"""


class InitCommand:
  """This class implements the init command.

  The register() method is called by the CLI startup code to install the init
  command information, and the cmd() function will be invoked if the init
  command was specified by the user.
  """

  def __init__(self):
    pass

  def register(self, args_subparsers, required_parsers, common_parsers):
    del common_parsers  # Unused by this register method.
    parent_parsers = required_parsers
    parser = args_subparsers.add_parser(
        'init', description=CMD_DESCRIPTION, parents=parent_parsers)

    mutually_exclusive = parser.add_mutually_exclusive_group(required=False)
    mutually_exclusive.add_argument(
        '--use-default-rtdb', help=USE_DEFAULT_RTDB_HELP, action='store_true')
    mutually_exclusive.add_argument(
        '--database-id',
        help=DATABASE_ID_HELP.format(
            default_database_id=SNAPSHOT_DEBUGGER_DEFAULT_DB_ID))

    parser.set_defaults(func=self.cmd)

    # Only some locations are supported, see:
    # https://firebase.google.com/docs/projects/locations#rtdb-locations
    #
    # If unsupported location is used, this error occurs
    # "error": {
    #   "code": 400,
    #   "message": "Request contains an invalid argument.",
    #   "status": "INVALID_ARGUMENT"
    # }
    # For now however we only support 'us-central1'
    parser.add_argument(
        '-l', '--location', help=LOCATION_HELP, default=DEFAULT_LOCATION)
    self.args_parser = parser

  def cmd(self, args, cli_services):
    self.services = cli_services
    self.user_output = cli_services.user_output
    self.firebase_management_service = \
        cli_services.firebase_management_service
    self.gcloud_service = cli_services.gcloud_service
    self.permissions_service = cli_services.permissions_service
    self.project_id = cli_services.project_id

    if args.location != DEFAULT_LOCATION:
      self.user_output.error('ERROR: Currently the only supported location is '
                             f"'{DEFAULT_LOCATION}'")
      raise SilentlyExitError

    # If the user does not have the required permissions this will emit an error
    # message and exit.
    self.permissions_service.check_required_permissions(REQUIRED_PERMISSIONS)

    # On error in any of the steps an error will be thrown and the cli would
    # exit. That means if the call returns, the step is complete and we can
    # proceed with the next step.
    self.check_and_handle_firebase_management_api_enabled()
    firebase_project = self.check_and_handle_firebase_enabled()
    self.check_and_handle_firebase_rtdb_management_api_enabled()
    database_instance = self.check_and_handle_database_instance(
        args=args, firebase_project=firebase_project)
    self.check_and_handle_db_init(database_instance)

    # If we make it here, everything is correctly initialized.
    self.user_output.normal(
        INIT_COMPLETE_MSG.format(
            project_id=self.project_id,
            db_name=database_instance.name,
            db_project=database_instance.project,
            db_url=database_instance.database_url,
            db_type=database_instance.type,
            db_state=database_instance.state))

  def check_and_handle_firebase_management_api_enabled(self):
    # If it's enabled, we can proceed, we'll be able to make queries to check
    # the project status.
    if self.gcloud_service.is_api_enabled(FIREBASE_MANAGMENT_API_SERVICE):
      return

    # If the api service is not enabled, then odds are they have not enabled
    # firebase for their project yet, so we treat this as the migration project
    # step.
    migration_link = MIGRATE_PROJECT_URL.format(project_id=self.project_id)
    firebase_api_link = FIREBASE_MANAGEMENT_API_URL.format(
        project_id=self.project_id)

    self.user_output.normal(
        MIGRATE_PROJECT_INSTRUCTIONS.format(
            migration_link=migration_link,
            firebase_console_link=FIREBASE_CONSOLE_URL.format(
                project_id=self.project_id),
            firebase_billing_link=FIREBASE_BILLING_URL,
            firebase_api_link=firebase_api_link))

    # A message has been printed prompting the user to perform an action, so
    # we exit now. We use error so the exit status is 1, as the project is not
    # yet initialized and ready to use.
    raise SilentlyExitError

  def check_and_handle_firebase_enabled(self):
    project_response = self.firebase_management_service.project_get()
    project_status = project_response.status

    if project_status == FirebaseProjectStatus.ENABLED:
      return project_response.firebase_project

    if project_status == FirebaseProjectStatus.NOT_ENABLED:
      # To get here it means the Firebase Management API is enabled, since
      # otherwise we would not know if the project is enabled for Firebase or
      # not. At this point the user will need to go through migrate project
      # flow. However for that to work the API must be disabled first. This is a
      # corner case where the Firebase Console UI will not be able to see the
      # project if the API is enabled.
      firebase_api_link = FIREBASE_MANAGEMENT_API_URL.format(
          project_id=self.project_id)

      self.user_output.normal(
          DISABLE_FIREBASE_API_MESSAGE.format(
              firebase_api_link=firebase_api_link))

      # A message has been printed prompting the user to perform an action, so
      # we exit now. We use error so the exit status is 1, as the project is not
      # yet initialized and ready to use.
      raise SilentlyExitError

    self.user_output.error(
        f"ERROR Unhandled project status '{project_status}', this should not "
        'happen')

    raise SilentlyExitError

  def check_and_handle_firebase_rtdb_management_api_enabled(self):
    if not self.gcloud_service.is_api_enabled(
        FIREBASE_RTDB_MANAGMENT_API_SERVICE):
      self.gcloud_service.enable_api(FIREBASE_RTDB_MANAGMENT_API_SERVICE)

  def check_and_handle_database_instance(self, args, firebase_project):
    database_id = self.get_database_id(
        args=args, firebase_project=firebase_project)

    instance_response = self.firebase_management_service.rtdb_instance_get(
        database_id)

    status = instance_response.status
    database_instance = None

    if status == DatabaseGetStatus.EXISTS:
      database_instance = instance_response.database_instance
    elif status == DatabaseGetStatus.DOES_NOT_EXIST:
      create_response = self.firebase_management_service.rtdb_instance_create(
          database_id=database_id, location=args.location)

      if create_response.status != DatabaseCreateStatus.SUCCESS:
        self.handle_database_create_failed(database_id, create_response)
      else:
        database_instance = create_response.database_instance

        # Since we've just created the DB, before proceeding we'll wait for it
        # to be accessible.
        self.wait_for_rtdb_to_be_accessible(database_instance)

    else:
      self.user_output.error(
          f"ERROR Unhandled database get instance status '{status}', this "
          'should not happen')

      raise SilentlyExitError

    return database_instance

  def get_database_id(self, args, firebase_project=None):
    if 'database_id' in args and args.database_id is not None:
      return args.database_id

    if 'use_default_rtdb' in args and args.use_default_rtdb:
      return self.services.get_firebase_default_rtdb_id(firebase_project)

    return self.services.get_snapshot_debugger_default_database_id()

  def handle_database_create_failed(self, database_id, create_response):
    if create_response.status == DatabaseCreateStatus.FAILED_PRECONDITION:
      # When a database create fails with error FAILED_PRECONDITION, one
      # potential reason is that they are on the spark billing plan, which only
      # allows one database per project, and it must be the default database.
      # Currently that's the only thing we can suggest the user check.
      project_billing_plan_link = BILLING_PLAN_URL.format(
          project_id=self.project_id)

      modify_billing_plan_link = project_billing_plan_link

      console_rtdb_link = CONSOLE_RTDB_URL.format(project_id=self.project_id)

      self.user_output.normal(
          CHECK_BILLING_PLAN_MESSAGE.format(
              database_id=database_id,
              project_id=self.project_id,
              firebase_billing_link=FIREBASE_BILLING_URL,
              console_rtdb_link=console_rtdb_link,
              project_billing_plan_link=project_billing_plan_link,
              modify_billing_plan_link=modify_billing_plan_link))
    else:
      self.user_output.error(
          f"ERROR Unhandled database create status '{create_response.status}', "
          'this should not happen')

    raise SilentlyExitError

  def check_and_handle_db_init(self, database_instance):
    rtdb_service = self.services.get_snapshot_debugger_rtdb_service(
        database_url=database_instance.database_url)

    # There is currently only one schema version.
    schema_version = '1'

    version = rtdb_service.get_schema_version()

    if version is None:
      rtdb_service.set_schema_version(schema_version)

  def wait_for_rtdb_to_be_accessible(self, database_instance):
    # Experimentally, it can take a short time (order of seconds) to not receive
    # 404s when attempting to access a newly created DB.
    db_url = database_instance.database_url
    self.user_output.normal(
        f'Waiting for newly created DB {db_url} to be accessible')
    rtdb_service = self.services.get_firebase_rtdb_rest_service(db_url)

    # We don't care about the return value here. Either the call will return,
    # indicating success and it was able to access the DB, otherwise it will
    # throw an exception and the CLI will exit.
    rtdb_service.get(db_path='', shallow=True, extra_retry_codes=[404])
