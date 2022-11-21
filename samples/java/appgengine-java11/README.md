# Snapshot Debugger Examples for Google App Engine Standard Environment for Java 11

NOTE: This file was copied
[README](https://github.com/GoogleCloudPlatform/java-docs-samples/blob/main/appengine-java11/README.md)
and modified for the sampls here.

## Prerequisites

### Download Maven

Some of these samples use the [Apache Maven][maven] build system. Before
getting started, be sure to [download][maven-download] and
[install][maven-install] it.  When you use Maven as described here, it will
automatically download the needed client libraries.

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

### Install the Snapshot Debugger CLI and enable Firebase

Follow the instructions beginning at [Before you
begin](../../../README.md#before-you-begin) through to and including [Enable
Firebase for your Google Cloud
Project](../../../README.md#enable-firebase-for-your-google-cloud-project) to
get the Snapshot Debugger CLI installed and your project configured to use
Firebase.

### Google Cloud Shell, Open JDK 11 setup:

If running in the Google Cloud Shell, to switch to an Open JDK 11 you can use:

```
   sudo update-alternatives --config java
   # And select the usr/lib/jvm/java-11-openjdk-amd64/bin/java version.
   # Also, set the JAVA_HOME variable for Maven to pick the correct JDK:
   export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
```

### App Engine Staging Directory and The Snapshot Debugger Java Agent

The App Engine Plugin will stage all the files to upload into App Engine
runtime in `${build.directory}/appengine-staging`. When deploying an [Uber
JAR](https://stackoverflow.com/questions/11947037/what-is-an-uber-jar), the JAR
is automatically copied into this staging directory and uploaded. It's possible
to copy other files into this staging directory and having them available in the
deployed App Engine runtime directory. This is required for the examples here as
the Snapshot Debugger Java
Agent must be deployed with your application.

- To stage the files to be uploaded:
```
mvn appengine:stage
```
