#!/usr/bin/env python3

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, date_trunc, row_number
from pyspark.sql.window import Window

spark = SparkSession.builder.remote("sc://localhost:15002") \
    .config("spark.sql.catalog.granica", "org.apache.iceberg.spark.SparkCatalog") \
    .config("spark.sql.catalog.granica.catalog-impl", "org.apache.iceberg.nessie.NessieCatalog") \
    .config("spark.sql.catalog.granica.uri", "http://nessie-catalog.data-platform.svc.cluster.local:19120/api/v1") \
    .config("spark.sql.catalog.granica.warehouse", "s3a://granica-us-east-1-data-lake/iceberg/") \
    .config("spark.sql.catalog.granica.s3.endpoint", "https://s3.us-east-1.amazonaws.com") \
    .getOrCreate()

df = spark.read.table("granica.granica_logs")

weekly_counts = (
    df.withColumn("week", date_trunc("week", col("timestamp")))
      .groupBy("week", "ip_address")
      .agg(count("*").alias("request_count"))
)

weekly_window = Window.partitionBy("week").orderBy(col("request_count").desc())
weekly_top5 = weekly_counts.withColumn("rank", row_number().over(weekly_window)).filter(col("rank") <= 5)

monthly_counts = (
    df.withColumn("month", date_trunc("month", col("timestamp")))
      .groupBy("month", "ip_address")
      .agg(count("*").alias("request_count"))
)

monthly_window = Window.partitionBy("month").orderBy(col("request_count").desc())
monthly_top5 = monthly_counts.withColumn("rank", row_number().over(monthly_window)).filter(col("rank") <= 5)

# Show results
print("=== Weekly Top 5 IPs ===")
weekly_top5.select("week", "ip_address", "request_count").show(100, truncate=False)

print("=== Monthly Top 5 IPs ===")
monthly_top5.select("month", "ip_address", "request_count").show(100, truncate=False)

spark.stop()
