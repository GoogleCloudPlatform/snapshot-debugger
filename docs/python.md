# Python Snapshot Debugger Agent

This section contains information for integrating and configuring the Python
Snapshot Debugger agent in different environments. Full configuration
information for the agent can be found at [Python Agent
Documentation][python-agent]

## Samples

See [samples/python][python-samples] for working examples of installing and
configuring the Python agent across different Google Cloud environments.

[python-agent]: https://github.com/GoogleCloudPlatform/cloud-debug-python/blob/main/README.md
[python-samples]: https://github.com/GoogleCloudPlatform/snapshot-debugger/tree/main/samples/python

## Running locally

It's also possible to run things outside of a Google Cloud environment, such
as locally. Here are some notes for doing so, which involves generating a
service account key so the agents are able to read/write from the Firebase RTDB
backend.

### Download service account credentials from Firebase.

1. Navigate to your project in the Firebase console service account page.
   Replace `PROJECT_ID` with your project’s ID.

    ```
    https://console.firebase.google.com/project/PROJECT_ID/settings/serviceaccounts/adminsdk
    ```

2. Click **Generate new private key** and save the key locally.

### Install and configure the agent

1. Download the Debugger agent.

    The easiest way to install the Python Debugger is with
    [pip](https://pypi.org/project/pip/)

    ```
    pip install google-python-cloud-debugger
    ```

2. Add the following lines as early as possible in your initialization code, such as in your main function, or in manage.py when using the Django web framework.

    ```
    try:
      import googleclouddebugger
      googleclouddebugger.enable(
        use_firebase=True,
        module='[MODULE]',
        version='[VERSION]',
        service_account_json_file='[PATH-TO-KEY-FILE]'
      )
    except ImportError:
      pass
    ```

    Where:
    *    `MODULE` is a name for your app, such as MyApp, Backend, or Frontend.
    *    `VERSION` is a version, such as v1.0, build_147, or v20170714.
    *    `PATH-TO-KEY-FILE` is the path to your Firebase private key.
