# Snapshot Debugger Examples for Google App Engine Standard Environment for Java 8

NOTE: This file was copied from
[java-docs-samples/appengine-java8/README.md](https://github.com/GoogleCloudPlatform/java-docs-samples/blob/main/appengine-java8/README.md)
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

### Google Cloud Shell, Open JDK 8 setup:

If running in the Google Cloud Shell, to switch to an Open JDK 8 you can use:

```
   sudo update-alternatives --config java
   # And select the /usr/lib/jvm/java-8-openjdk-amd64/jre/bin/java version.
   # Also, set the JAVA_HOME variable for Maven to pick the correct JDK:
   export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
```

### App Engine Staging Directory and The Snapshot Debugger Java Agent

The App Engine Plugin will stage all the files to upload into App Engine runtime
in `${build.directory}/appengine-staging`. It's possible to copy other files
into this staging directory and having them available in the deployed App Engine
runtime directory. This is required for the examples here as the Snapshot
Debugger Java Agent must be deployed with your application.

- To stage the files to be uploaded:
```
mvn appengine:stage
```

This means the deploy would be done in three stages,
1. `mvn package appengine:stage`
2. Add files to `${build.directory}/appengine-staging`
3. `gcloud app deploy ${build.directory}/appengine-staging/app.yaml`

While it is possible to place the agent files somewhere under your src WEB-INF
directory and have maven automatically deploy it in one step, this may not be
desirable, as it may end up in your `__static__` directory. In addition if you
place it somewhere under the WEB-INFO lib directory the classes in the agent's
jar files will then potentially conflict with the jar files intended for your
application.  It is important that the two be kept separate.

### GAE_AGENTPATH_OPTS Environment Variable

To get the JVM in the App Engine Java 8 runtime to load a user supplied agent,
the `GAE_AGENTPATH_OPTS` environment variable must be configured in the
`appengine-web.xml` file. This environment variable is a space separated list of
`agentpath` config entries of agents to load. Each entry begins with the
relative path in the user's deployment to the agent .so file.  See
[helloworld](helloworld/README.md#deploy-the-application) for an example.
