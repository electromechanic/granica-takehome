#!/usr/bin/env python3
from pyspark.sql import SparkSession

spark = SparkSession.builder.remote("sc://localhost:15002") \
    .config("spark.sql.catalog.granica", "org.apache.iceberg.spark.SparkCatalog") \
    .config("spark.sql.catalog.granica.catalog-impl", "org.apache.iceberg.nessie.NessieCatalog") \
    .config("spark.sql.catalog.granica.uri", "http://nessie-catalog.data-platform.svc.cluster.local:19120/api/v1") \
    .config("spark.sql.catalog.granica.warehouse", "s3a://granica-us-east-1-data-lake/iceberg/") \
    .config("spark.sql.catalog.granica.s3.endpoint", "https://s3.us-east-1.amazonaws.com") \
    .getOrCreate()

# daily partitioning
spark.sql("""
    CREATE TABLE IF NOT EXISTS granica.granica_logs (
        ip_address STRING,
        timestamp TIMESTAMP,
        method STRING,
        endpoint STRING,
        protocol STRING,
        status_code STRING,
        bytes STRING,
        user_agent STRING
    )
    USING iceberg
    PARTITIONED BY (days(timestamp))
    TBLPROPERTIES (
        'format-version' = '2'
    )
""")

print("granica_logs table created")
