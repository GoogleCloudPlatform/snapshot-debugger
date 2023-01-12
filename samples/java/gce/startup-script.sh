#! /bin/bash
# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# [START script]
set -e
set -v

# Talk to the metadata server to get the project id
PROJECTID=$(curl -s "http://metadata.google.internal/computeMetadata/v1/project/project-id" -H "Metadata-Flavor: Google")

echo "Project ID: ${PROJECTID}"

# Install dependencies from apt
apt-get update
apt-get install -yq openjdk-11-jdk git maven wget curl

mvn --version

# Install the Snapshot Debugger
mkdir /opt/cdbg
wget -qO- https://github.com/GoogleCloudPlatform/cloud-debug-java/releases/latest/download/cdbg_java_agent_gce.tar.gz | tar xvz -C /opt/cdbg

# Jetty Setup
mkdir -p /opt/jetty/temp
mkdir -p /var/log/jetty

# Get Jetty
curl -L https://repo1.maven.org/maven2/org/eclipse/jetty/jetty-distribution/9.4.13.v20181111/jetty-distribution-9.4.13.v20181111.tar.gz -o jetty9.tgz
tar xf jetty9.tgz  --strip-components=1 -C /opt/jetty

# Add a Jetty User
useradd --user-group --shell /bin/false --home-dir /opt/jetty/temp jetty

cd /opt/jetty
# Add running as "jetty"
java -jar /opt/jetty/start.jar --create-startd --add-to-start=setuid
cd /

# Clone the source repository.
# TODO: Update to not need the branch checkout
git clone https://github.com/GoogleCloudPlatform/snapshot-debugger.git /opt/app/snapshot-debugger
cd /opt/app/snapshot-debugger
git checkout samples-java-gce
cd samples/java/gce

# Build the .war file and then unpack it to /opt/jetty/webapps/root
# Notes:
#   - By naming the directory 'root', it will run as the root servlet.
#   - We use a directory containing the unpacked webapp vs using 'root.war'
#     because this way the libs and class files will be in a known location
#     that the agent can access. When using a war file jetty will unpack it
#     somewhere in the temp directory and the agent will not be able to find
#     the classes to set breakpoints.
#   - Additionally, the java agent will automatically look in
#     ${jetty.base}/webapps/root/WEB-INF/[lib, classes] ('ROOT' is also
#     checked). If a different name other than 'root' or 'ROOT' is used for the
#     directory name the 'cdbg_extra_class_path' agent parameter would need to
#     be provided to the agent. See
#     https://github.com/GoogleCloudPlatform/cloud-debug-java#extra-classpath
#     for more information.
mvn clean package -q
WAR_FILE=`pwd`/target/getting-started-gce-1.0-SNAPSHOT.war
mkdir /opt/jetty/webapps/root
pushd /opt/jetty/webapps/root
jar -xvf ${WAR_FILE}
popd


# Make sure "jetty" owns everything.
chown --recursive jetty /opt/jetty

# Configure the default paths for the Jetty service
cp /opt/jetty/bin/jetty.sh /etc/init.d/jetty
echo "JETTY_HOME=/opt/jetty" > /etc/default/jetty
{
  echo "JETTY_BASE=/opt/jetty"
  echo "TMPDIR=/opt/jetty/temp"
  echo "JAVA_OPTIONS='-agentpath:/opt/cdbg/cdbg_java_agent.so=--use-firebase=true -Dcom.google.cdbg.version=v1 -Dcom.google.cdbg.module=gce-java-sample -Djetty.http.port=80'"
  echo "JETTY_LOGS=/var/log/jetty"
} >> /etc/default/jetty

# Reload daemon to pick up new service
systemctl daemon-reload

# Install logging monitor. The monitor will automatically pickup logs sent to syslog.
curl -sSO https://dl.google.com/cloudagents/add-logging-agent-repo.sh
sudo bash add-logging-agent-repo.sh --also-install

service google-fluentd restart &

service jetty start
service jetty check

echo "Startup Complete"
# [END script]
