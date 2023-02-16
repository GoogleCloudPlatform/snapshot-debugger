# Snapshot Debugger Examples for Google App Engine Standard Environment for Java 11

NOTE: This file was copied from
[java-docs-samples/appengine-java11/README.md](https://github.com/GoogleCloudPlatform/java-docs-samples/blob/main/appengine-java11/README.md)
and modified for the Snapshot Debugger samples here.

## Prerequisites

### Setup the Project and the Snapshot Debugger CLI

1.  Perform all [Prerequisite Steps](../../app_engine_standard_prerequisites.md)

### Download Maven

Some of these samples use the [Apache Maven][maven] build system. Before
getting started, be sure to [download][maven-download] and
[install][maven-install] it.  When you use Maven as described here, it will
automatically download the needed client libraries.

[maven]: https://maven.apache.org
[maven-download]: https://maven.apache.org/download.cgi
[maven-install]: https://maven.apache.org/install.html

### Install Google Cloud `gcloud` CLI App Engine extension for Java

1. `gcloud` should already have been installed as part of an earlier step, if
   not [install][install-gcloud] and [initialize][initialize-gcloud] the Google
   Cloud CLI.
1. Install the [gcloud component][managing-components] that includes the App
   Engine extension for Java.

   If you used the `apt` or `yum` package managers to install the gcloud CLI,
   [use those same package managers to install the gcloud component][external-package-managers].

   Otherwise, use the following command:

   ```
   gcloud components install app-engine-java
   ```

[install-gcloud]: https://cloud.google.com/sdk/docs/install
[initialize-gcloud]: https://cloud.google.com/sdk/docs/initializing
[managing-components]: https://cloud.google.com/sdk/docs/managing-components
[external-package-managers]: https://cloud.google.com/sdk/docs/components#external_package_managers

### Google Cloud Shell, Open JDK 11 setup:

If running in the Google Cloud Shell, to switch to an Open JDK 11 you can use:

```
   sudo update-alternatives --config java
   # And select the usr/lib/jvm/java-11-openjdk-amd64/bin/java version.
   # Also, set the JAVA_HOME variable for Maven to pick the correct JDK:
   export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
```

### Servlet Runtime

The Java 11 runtime requires that your application have a `Main` class that
starts a web server.
[`appengine-simple-jetty-main`](appengine-simple-jetty-main) is a shared
artifact that provides a Jetty Web Server for the servlet based runtime.
Packaged as a jar, the Main Class will load a directory containing a webapp
passed as an argument, as the context root of the web application listening to
port 8080.  Some samples will use this runtime and provide the exploded webapp
directory as an argument in the App Engine `app.yaml` entrypoint field.

To note, the original
[java-docs-samples/appengine-java11/appengine-simple-jetty-main](https://github.com/GoogleCloudPlatform/java-docs-samples/tree/main/appengine-java11/appengine-simple-jetty-main)
works by accepting a WAR file. Here we have modified it to take in a directory
containing the webapp (the exploded WAR file) instead. The reason for this is
that when Jetty explodes a WAR file it is placed in a temp directory, which
means the Snapshot Debugger Java agent will not be able to find the class files
and will be unable to set breakpoints.

### App Engine Staging Directory and The Snapshot Debugger Java Agent

The App Engine Plugin will stage all the files to upload into App Engine runtime
in `${build.directory}/appengine-staging`. When deploying an [Uber
JAR](https://stackoverflow.com/questions/11947037/what-is-an-uber-jar), the JAR
is automatically copied into this staging directory and uploaded. It's possible
to copy other files into this staging directory and having them available in the
deployed App Engine runtime directory. This is required for the examples here as
the Snapshot Debugger Java Agent must be deployed with your application.

- To stage the files to be uploaded:
```
mvn package appengine:stage
```
