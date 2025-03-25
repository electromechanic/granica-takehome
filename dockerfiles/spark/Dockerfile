FROM apache/spark:3.5.2

ENV SPARK_JARS_DIR=/opt/spark/jars
WORKDIR $SPARK_JARS_DIR

# Download required JARs from Maven Central
RUN wget -q https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/1.8.0/iceberg-spark-runtime-3.5_2.12-1.8.0.jar
RUN wget -q https://repo1.maven.org/maven2/org/projectnessie/nessie-integrations/nessie-spark-extensions-3.5_2.12/0.103.2/nessie-spark-extensions-3.5_2.12-0.103.2.jar
RUN wget -q https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar
RUN wget -q https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.539/aws-java-sdk-bundle-1.12.539.jar
RUN wget -q https://repo1.maven.org/maven2/org/apache/spark/spark-connect_2.12/3.5.2/spark-connect_2.12-3.5.2.jar

