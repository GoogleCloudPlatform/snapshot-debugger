# Snapshot Debugger Examples for Google App Engine Flexible Environment

> **NOTE**
> This file was copied from
> [java-docs-samples/appengine-flexible/README.md](https://github.com/GoogleCloudPlatform/java-docs-samples/blob/main/appengine-flexible/README.md)
> and modified for the Snapshot Debugger samples here.

## Prerequisites

### Download Maven

Some of these samples use the [Apache Maven][maven] build system. Before getting
started, be sure to [download][maven-download] and [install][maven-install] it.
When you use Maven as described here, it will automatically download the needed
client libraries.

[maven]: https://maven.apache.org
[maven-download]: https://maven.apache.org/download.cgi
[maven-install]: https://maven.apache.org/install.html

### Create a Project in the Google Cloud Platform Console

If you haven't already created a project, create one now. Projects enable you to
manage all Google Cloud Platform resources for your app, including deployment,
access control, billing, and services.

1. Open the [Cloud Platform Console][cloud-console].
1. In the drop-down menu at the top, select **Create a project**.
1. Give your project a name.
1. Make a note of the project ID, which might be different from the project
   name. The project ID is used in commands and in configurations.

[cloud-console]: https://console.cloud.google.com/

### Install Google Cloud `gcloud` CLI along with App Engine extension for Java

1. See [Install gcloud](../../README.md#install-google-cloud-gcloud-cli)
1. Install the [gcloud component][managing-components] that includes the App
   Engine extension for Java.

   If you used the `apt` or `yum` package managers to install the gcloud CLI,
   [use those same package managers to install the gcloud component][external-package-managers].

   Otherwise, use the following command:

   ```
   gcloud components install app-engine-java
   ```

[managing-components]: https://cloud.google.com/sdk/docs/managing-components
[external-package-managers]: https://cloud.google.com/sdk/docs/components#external_package_managers

### Create an App Engine application

Run the following command to select a region and create an App Engine application:

```
gcloud app create
```

In the event this command was already run on the project, the invocation will
simply error out and provide an message saying it has already been done.

### Install the Snapshot Debugger CLI and enable Firebase

Follow the instructions beginning at [Before you
begin](../../../README.md#before-you-begin) through to and including [Enable
Firebase for your Google Cloud
Project](../../../README.md#enable-firebase-for-your-google-cloud-project) to
get the Snapshot Debugger CLI installed and your project configured to use
Firebase.

### Google Cloud Shell, Open JDK 8 setup:

If running in the Google Cloud Shell, to switch to an Open JDK 8 you can use:

```
   sudo update-alternatives --config java
   # And select the usr/lib/jvm/java-8-openjdk-amd64/jre/bin/java version.
   # Also, set the JAVA_HOME variable for Maven to pick the correct JDK:
   export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
```

### Available Runtimes

There are two Google provided Java runtimes available:
- [The Java 8 / Jetty 9 runtime](https://cloud.google.com/appengine/docs/flexible/java/dev-jetty9)
  - Provides OpenJDK 8 and Eclipse Jetty 9 with support for the Java Servlet 3.1
    Specification.
- [The Java 8 runtime](https://cloud.google.com/appengine/docs/flexible/java/dev-java-only)
  - Does not include any web-serving framework. The only requirement is that
    your app should listen and respond on port 8080.

### Runtime Customization and JAVA_USER_OPTS

The runtime customization feature is used in the samples to add the Snapshot
Debugger agent. In addition, the JAVA_USER_OPTS environment variable is used to
set the `-agentpath` JVM option to load the agent. See the links below for more
information on these options:

- The Java 8 / Jetty 9 runtime
  - [Customization](https://cloud.google.com/appengine/docs/flexible/java/dev-jetty9#customize)
  - [Jetty 9 runtime environment variables](https://cloud.google.com/appengine/docs/flexible/java/dev-jetty9#variables)
  - [Java 8 runtime environment variables are additionally available](https://cloud.google.com/appengine/docs/flexible/java/dev-java-only#variables)
- The Java 8 Runtime
  - [Customization](https://cloud.google.com/appengine/docs/flexible/java/dev-java-only#customizing)
  - [Available environment variables](https://cloud.google.com/appengine/docs/flexible/java/dev-java-only#variables)
