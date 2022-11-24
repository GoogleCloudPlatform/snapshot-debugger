# Embedded Jetty Server for Google App Engine Standard with Java 11

> **Note**
> This directory was copied from [appengine-java11/appengine-simple-jetty-main](https://github.com/GoogleCloudPlatform/java-docs-samples/tree/main/appengine-java11/appengine-simple-jetty-main).

For the Java 11 runtime, your application must have a `Main` class that starts a
web server. This sample is a shared artifact that provides a `Main` class to
instantiate an HTTP server to run an embedded web application `WAR` file.

## Install the dependency

This sample is used as a dependency and must be installed locally:

```
mvn install
```

## Using the dependency

See [`helloworld-servlet`](../helloworld-servlet) for a complete example.

Your project's `pom.xml` needs to be updated accordingly:

- Add the `appengine-simple-jetty-main` dependency:

```
<dependency>
  <groupId>com.example.appengine.demo</groupId>
  <artifactId>simple-jetty-main</artifactId>
  <version>1</version>
  <scope>provided</scope>
</dependency>
```

- On deployment, the App Engine runtime uploads files located in
`${build.directory}/appengine-staging`. Add the `maven-dependency-plugin` to
the build in order to copy dependencies to the correct folder:

```
<plugin>
  <groupId>org.apache.maven.plugins</groupId>
  <artifactId>maven-dependency-plugin</artifactId>
  <version>3.1.1</version>
  <executions>
    <execution>
      <id>copy</id>
      <phase>prepare-package</phase>
      <goals>
        <goal>copy-dependencies</goal>
      </goals>
      <configuration>
        <outputDirectory>
          ${project.build.directory}/appengine-staging
        </outputDirectory>
      </configuration>
    </execution>
  </executions>
</plugin>
```

See [`helloworld-servlet`](../helloworld-servlet) for how to write your
`app.yaml` file to use the dependency by specifying the entry point.
