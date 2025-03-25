# Granica Takehome Assignment

This platform is built using EKS, S3 and RDS for the AWS resource. For the data catalog it uses Nessie with their official helm chart, this data catalog is using postgtres aurora to store metadata and commit data. Spark is deployed using the official Apache Spark operator helm chart (the kubeflow chart doesn't support peristant clusters, transient jobs only). Spark is used to write, query, and proccess data leveraging Nessie for indexing and metadata management.


| Software | Version |
| ---------- | --------- |
| Spark    | 3.5.2   |
| Scala    | 2.12    |
| Nessie   | 0.103.2 |
| Iceberg  | 1.8.0   |
| Java     | 11      |

I'll walk through the build process step by step. It is assumed that all commands are run from the root of the repo unless specified otherwise. You will need aws access with the ability to deploy buckets, kms keys, iam roles, role policies, eks clusters, and rds clusters. I ran this using Kubuntu 24.04, you may need to make adjustment if you're using OSX, Windows or another Linux flavor. I'm going to use basic port forwarding to demonstrate this.

To get started go to the terraform resources directory, update the values to your needs and apply the config

```
cd terraform/resources
terraform init && terraform apply
```

This will stand up an s3 bucket for the datalake and database cluster. The database credentials are written to aws secrets manager.

For the EKS cluster, i have a custom tool that i built that runs in a job pod and is configured with environment variables. It's a WIP and the jobs used will be integrated in to an operator crd later. If you want to know more, let me know and i'll add you to the private repo and demonstrate how it works. You can see the manifests for this deployment in ./eks-deployment. You can see the logs files in /artifacts

Once the cluster is up, add it to your kubeconfig

aws eks update-kubeconfig --region us-east-1 --name granica-platform

Create the data-platform namespace, aws key secret, and database credentials secret

```
kubectl create namespace data-platform

kubectl create secret generic aws-keys
--namespace data-platform
--from-literal=aws_access_key=<"your access key key">
--from-literal=aws_secret_key=<"your secret key">

kubectl create secret generic nessie-db-creds
--namespace data-platform
--from-literal=username=master
--from-literal=password=<"your password">
```

Deploy Nessie data catalog and port forward to the web ui

```
helm repo add nessie-helm https://charts.projectnessie.org

helm upgrade
--install nessie-catalog nessie-helm/nessie
-f platform-components/nessie-catalog.yaml
-n data-platform

kubectl port-forward services/nessie-catalog 19120:19120 -n data-platform
```

Build a spark image with the Nessie and Iceberg dependencies, deploy to ECR

```
aws ecr get-login-password | docker login --username AWS --password-stdin <'aws account number'>.dkr.ecr.us-east-1.amazonaws.com
aws ecr create-repository --repository-name granica-spark
docker build -t <'aws account number'>.dkr.ecr.us-east-1.amazonaws.com/granica-spark:3.5.2-iceberg-v2 dockerfiles/spark/.
docker push <'aws account number'>.dkr.ecr.us-east-1.amazonaws.com/granica-spark:3.5.2-iceberg-v2
```

Deploy the Spark operator
note: You will need to clone down the operator repo and you'll
also need to use java17 to generate the CRDs, dependencies are
jdk17, jre17, and th mikefarah build of yq
https://github.com/mikefarah/yq?tab=readme-ov-file#install

Clone this outside of the dataplatform repo and cd in to the root of the spark-kubernetes-operator repo

```
git clone git@github.com:apache/spark-kubernetes-operator.git

./gradlew spark-operator-api:relocateGeneratedCRD

kubectl apply -f build-tools/helm/spark-kubernetes-operator/crds/

helm upgrade
    --install spark-kubernetes-operator
    -f <'path to dataplatform repo>/platform-components/spark-operator.yaml
    -n data-platform
    build-tools/helm/spark-kubernetes-operator/
```

Launch the Spark cluster from the CRs and connect-server pod and port forward to the webui and connect-server

```
kubectl apply -f platform-components/spark-cluster.yaml
kubectl apply -f platform-components/spark-connect.yaml
kubectl port-forward pods/granica-spark-cluster-master-0 8080:8080 -n data-platform
port-forward services/spark-connect-server 15002:15002 -n data-platform
```

Now we can run Spark jobs from the desktop, I'm going to use pyspark to demonstrate.
note: you'll need to create an pyenv using your tool of choice and install the dependencies, I'm using miniconda
You wil also need to verify your AWS access key and secret key are present in your environment vars

```
conda create -n pyspark
conda activate pyspark
conda install pyspark==3.5.4
conda install grpcio protobuf google-api-core grpcio-status
env | grep AWS_
```

To have an interactive session with Spark using pyspark start a python shell

`python3`

Then instantiate a session with the connect server, and start running queries

```
from pyspark.sql import SparkSession
spark = SparkSession.builder.remote("sc://localhost:15002")
    .config("spark.sql.catalog.granica", "org.apache.iceberg.spark.SparkCatalog")
    .config("spark.sql.catalog.granica.catalog-impl", "org.apache.iceberg.nessie.NessieCatalog")
    .config("spark.sql.catalog.granica.uri", "http://nessie-catalog.data-platform.svc.cluster.local:19120/api/v1")
    .config("spark.sql.catalog.granica.warehouse", "s3a://granica-us-east-1-data-lake/iceberg/")
    .config("spark.sql.catalog.granica.s3.endpoint", "https://s3.us-east-1.amazonaws.com")
    .getOrCreate()

spark.sql("SHOW TABLES IN granica").show()

spark.sql("""
CREATE TABLE granica.test_table (
id INT,
message STRING
)
USING iceberg
""")

spark.sql("""
DROP TABLE granica.test_table
""")

spark.sql("""
INSERT INTO granica.test_table VALUES
(1, 'hello'),
(2, 'from'),
(3, 'Spark Connect!')
""")

spark.sql("SELECT * FROM granica.test_table").show()
```

For loading log entries per the requirements there's a spark job in /jobs/generate_logs/ move to the generate_logs directory and run the jobs for creating the tables and loading the logs. This will produce 3 monts of web logs

```
cd jobs/generate_logs/
./create_log_table.py
./generate_logs.py
```

The queries to get the top 5 stats are in jobs/top_5/
There are three jobs, one for devices, one for browser, and one for IPs. They do weekly and monthly counts.
There are a lot of days in three months so the output for daily top 5 is rather large. It's more reasonable to start an interactive python session and use spark sql queries to look at individual days. Top 5 device type is strange because there's only three device types, mobile, tablet and desktop. User agent can be interesting, we can get total request counts by device type on a given day

```
spark.sql("""
SELECT user_agent, COUNT(*) AS requests
    FROM granica.granica_logs
    WHERE DATE(timestamp) = DATE('2025-03-01')
    GROUP BY user_agent
    ORDER BY requests DESC
    LIMIT 5
""").show()

spark.sql("""
SELECT ip_address, COUNT(*) AS requests
    FROM granica.granica_logs
    WHERE DATE(timestamp) = DATE('2025-03-01')
    GROUP BY ip_address
    ORDER BY requests DESC
    LIMIT 5
""").show()

spark.sql("""
SELECT
    CASE
        WHEN LOWER(user_agent) LIKE '%mobile%' THEN 'Mobile'
        WHEN LOWER(user_agent) LIKE '%tablet%' THEN 'Tablet'
        WHEN LOWER(user_agent) LIKE '%android%' THEN 'Mobile'
        WHEN LOWER(user_agent) LIKE '%iphone%' THEN 'Mobile'
        WHEN LOWER(user_agent) LIKE '%ipad%' THEN 'Tablet'
        WHEN LOWER(user_agent) LIKE '%windows%' THEN 'Desktop'
        WHEN LOWER(user_agent) LIKE '%macintosh%' THEN 'Desktop'
    ELSE 'Other'
    END AS device_type,
    COUNT(*) AS requests
    FROM granica.granica_logs
    WHERE DATE(timestamp) = DATE('2025-03-01')
    GROUP BY device_type
    ORDER BY requests DESC
    LIMIT 5
""").show()
```

# TODO: set up metrics, and store outputs in other tables, design diagram and scaling estimates
