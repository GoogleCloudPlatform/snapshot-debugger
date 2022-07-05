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
"""A collection of types representing Firebase entities and responses.

The types here help work with the data and response messages from Firebase.
"""

from enum import Enum

FIREBASE_MANAGMENT_API_SERVICE = 'firebase.googleapis.com'
FIREBASE_RTDB_MANAGMENT_API_SERVICE = 'firebasedatabase.googleapis.com'


class FirebaseProjectStatus(Enum):
  ENABLED = 1
  NOT_ENABLED = 2


class FirebaseProject:
  """Accepts a FirebaseProject REST resource and retrieves desired values.

  Documentation for what's expected to be in a FirebaseProject can be found
  here:
  https://firebase.google.com/docs/projects/api/reference/rest/v1beta1/projects#FirebaseProject

  Attributes:
    default_rtdb_instance: The project's default RTDB database instance. This
    value is the name of the instance (not a URL). A value of None indicates the
    project has no default instance.
  """

  def __init__(self, firebase_project):
    # We are only retrieving the information we require.

    # If this value is None that means the Project's default database has not
    # been created.
    self.default_rtdb_instance = self.get_default_rtdb_instance(
        firebase_project)

  @staticmethod
  def get_default_rtdb_instance(firebase_project):
    url = None

    try:
      url = firebase_project['resources']['realtimeDatabaseInstance']
    except KeyError:
      # This is fine, there's no guarantee it exists
      pass

    return url


class FirebaseProjectGetResponse:
  """Represents the response of a project get request.

  The firebase_project field is only valid if the status is ENABLED, it will
  be None otherwise.
  """

  def __init__(self,
               status: FirebaseProjectStatus,
               firebase_project: FirebaseProject = None):
    """Initializes the FirebaseProjectGetResponse instance.

    Args:
      status: Indicates if the FirebaseProject is enabled or not.
      firebase_project: Information about the project as returned by the get
        command. Should be None if status is not ENABLED.
    """
    self.status = status
    self.firebase_project = firebase_project


class DatabaseGetStatus(Enum):
  EXISTS = 1
  DOES_NOT_EXIST = 2


class DatabaseCreateStatus(Enum):
  SUCCESS = 1

  # When the create instance fails with error 400 and provides a status of
  # FAILED_PRECONDITION. One reason found for this is that the project is on the
  # spark billing plan, which only allows one database, which must be the
  # default database. In order to be able to create an arbitrary instance they
  # would need to upgrade to the blaze billing plan.
  FAILED_PRECONDITION = 2


class DatabaseInstance:
  """Accepts a DatabaseInstance REST resource and retrieves desired values.

  Documentation for what's expected to be in a DatabaseInstance can be found
  here:
  https://firebase.google.com/docs/reference/rest/database/database-management/rest/v1beta/projects.locations.instances#resource:-databaseinstance
  """

  def __init__(self, database_instance):
    """Initializes a DatabaseInstance with a dict of database_instance data.

    Args:
      database_instance: A DatabaseInstance REST resource. See class docstring
        for link to relevant documentation.

    Raises:
      ValueError: If the provided database_instance is missing required fields.
        It will contain a message describing the error.
    """
    try:
      self.name = database_instance['name']
      self.project = database_instance['project']
      self.database_url = database_instance['databaseUrl']
      self.type = database_instance['type']
      self.state = database_instance['state']
    except KeyError as e:
      missing_key = e.args[0]
      error_message = ('DatabaseInstance is missing expected field '
                       f"'{missing_key}' instance: {database_instance}")
      raise ValueError(error_message) from e


class DatabaseCreateResponse:
  """Represents the response of a database create request.

  The database_instance field is only valid if the status is SUCCESS, it will
  be None otherwise.
  """

  def __init__(self,
               status: DatabaseCreateStatus,
               database_instance: DatabaseInstance = None):
    """Initializes the DatabaseCreateResponse instance.

    Args:
      status: Indicates if the create request was successful or not.
      database_instance: Information about the database as returned by the
        create command. Should be None if status is not SUCCESS.
    """
    self.status = status
    self.database_instance = database_instance


class DatabaseGetResponse:
  """Represents the response of a database get request.

  The database_instance field is only valid if the status is EXISTS, it will
  be None otherwise.
  """

  def __init__(self,
               status: DatabaseGetStatus,
               database_instance: DatabaseInstance = None):
    """Initializes the DatabaseCreateResponse instance.

    Args:
      status: Indicates if the get request found the database existed or not.
      database_instance: Information about the database as returned by the get
        command. Should be None if status is not EXISTS.
    """
    self.status = status
    self.database_instance = database_instance
