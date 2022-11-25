# We are customizing the Java 8 / Jetty 9 Runtime
# See https://cloud.google.com/appengine/docs/flexible/java/dev-jetty9
# for more information on these first two lines.
FROM gcr.io/google-appengine/jetty
COPY ./flexible-helloworld-1.0-SNAPSHOT.war $APP_DESTINATION

# Until the Cloud Debugger has been fully turned down, the rutime images will
# continue to contain the current Cloud Debugger Java agent located in
# /opt/cdbg. Here we remove it if it exists.
RUN rm -rf /opt/cdbg

# Add the Snapshot Debugger Java Agent
ADD https://github.com/GoogleCloudPlatform/cloud-debug-java/releases/latest/download/cdbg_java_agent_gce.tar.gz /opt/cdbg/
RUN tar Cxfvz /opt/cdbg /opt/cdbg/cdbg_java_agent_gce.tar.gz --no-same-owner \
  && rm /opt/cdbg/cdbg_java_agent_gce.tar.gz
