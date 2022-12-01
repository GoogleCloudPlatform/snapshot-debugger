# We are customizing the Java 8 Runtime
# See https://cloud.google.com/appengine/docs/flexible/java/dev-java-only#customizing
# for more information on these first two lines.
FROM gcr.io/google-appengine/openjdk:8
COPY ./helloworld-springboot-0.0.1-SNAPSHOT.jar $APP_DESTINATION

# Until the Cloud Debugger has been fully turned down, the rutime image will
# continue to contain the current Cloud Debugger Java agent located in
# /opt/cdbg. Here we remove it if it exists.
RUN rm -rf /opt/cdbg

# Add the Snapshot Debugger Java Agent
ADD https://github.com/GoogleCloudPlatform/cloud-debug-java/releases/latest/download/cdbg_java_agent_gce.tar.gz /opt/cdbg/
RUN tar Cxfvz /opt/cdbg /opt/cdbg/cdbg_java_agent_gce.tar.gz --no-same-owner \
  && rm /opt/cdbg/cdbg_java_agent_gce.tar.gz

