#!/usr/bin/env python3

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, date_trunc, lower, when

# Start Spark session via Spark Connect
spark = SparkSession.builder.remote("sc://localhost:15002") \
    .config("spark.sql.catalog.granica", "org.apache.iceberg.spark.SparkCatalog") \
    .config("spark.sql.catalog.granica.catalog-impl", "org.apache.iceberg.nessie.NessieCatalog") \
    .config("spark.sql.catalog.granica.uri", "http://nessie-catalog.data-platform.svc.cluster.local:19120/api/v1") \
    .config("spark.sql.catalog.granica.warehouse", "s3a://granica-us-east-1-data-lake/iceberg/") \
    .config("spark.sql.catalog.granica.s3.endpoint", "https://s3.us-east-1.amazonaws.com") \
    .getOrCreate()

df = spark.read.table("granica.granica_logs")

# classify device type from user agent
df_devices = df.withColumn(
    "device_type",
    when(lower(col("user_agent")).rlike("mobile|android|iphone"), "mobile")
    .when(lower(col("user_agent")).rlike("tablet|ipad"), "tablet")
    .otherwise("desktop")
)

# weekly top 5
weekly_top = (
    df_devices.withColumn("week", date_trunc("week", col("timestamp")))
    .groupBy("week", "device_type")
    .agg(count("*").alias("request_count"))
    .orderBy("week", "request_count", ascending=[True, False])
)

# monthly top 5
monthly_top = (
    df_devices.withColumn("month", date_trunc("month", col("timestamp")))
    .groupBy("month", "device_type")
    .agg(count("*").alias("request_count"))
    .orderBy("month", "request_count", ascending=[True, False])
)


print("=== Weekly Top 5 Devices ===")
weekly_top.show(36, truncate=False)

print("=== Monthly Top 5 Devices ===")
monthly_top.show(15, truncate=False)

spark.stop()
