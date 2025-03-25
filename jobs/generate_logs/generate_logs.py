#!/usr/bin/env python3
import random
import datetime
from pathlib import Path
from pyspark.sql import SparkSession
from pyspark.sql.functions import regexp_extract, to_timestamp
from pyspark.sql.types import IntegerType

# === CONFIG ===
start = datetime.datetime(2024, 12, 25)
end = datetime.datetime(2025, 3, 25)
logs_per_minute = 45
batch_size = 20000

user_agent_files = [
    "Android+Webkit+Browser.txt",
    "Chrome.txt",
    "Edge.txt",
    "Firefox.txt",
    "Internet+Explorer.txt",
    "Opera.txt",
    "Safari.txt"
]
data_dir = Path("./useragents")
log_pattern = r'^(\S+) - - \[(.*?)\] "(.*?) (.*?) (.*?)" (\d{3}) (\d+) "-" "(.*?)"$'

# === LOAD USER AGENTS ===
user_agents = []
for fname in user_agent_files:
    path = data_dir / fname
    with open(path, "r", encoding="utf-8") as f:
        user_agents += [line.strip() for line in f if line.strip()]

assert user_agents, "user agent files empty"

# === TIME RANGE ===
total_minutes = int((end - start).total_seconds() / 60)
total_logs = total_minutes * logs_per_minute

# === SPARK SESSION ===
spark = SparkSession.builder.remote("sc://localhost:15002") \
    .config("spark.sql.catalog.granica", "org.apache.iceberg.spark.SparkCatalog") \
    .config("spark.sql.catalog.granica.catalog-impl", "org.apache.iceberg.nessie.NessieCatalog") \
    .config("spark.sql.catalog.granica.uri", "http://nessie-catalog.data-platform.svc.cluster.local:19120/api/v1") \
    .config("spark.sql.catalog.granica.warehouse", "s3a://granica-us-east-1-data-lake/iceberg/") \
    .config("spark.sql.catalog.granica.s3.endpoint", "https://s3.us-east-1.amazonaws.com") \
    .getOrCreate()

# === GENERATOR ===
def generate_log_line(i):
    ts = start + datetime.timedelta(seconds=i * 60 / logs_per_minute)
    dt_str = ts.strftime("%d/%b/%Y:%H:%M:%S +0000")
    ip = ".".join(str(random.randint(0, 255)) for _ in range(4))
    agent = random.choice(user_agents)
    path = f"/path{random.randint(1, 100)}.html"
    size = random.randint(200, 5000)
    return f'{ip} - - [{dt_str}] "GET {path} HTTP/1.1" 200 {size} "-" "{agent}"'

# === BATCH WRITE ===
for batch_start in range(0, total_logs, batch_size):
    print(f"generating logs {batch_start} to {min(batch_start + batch_size, total_logs)}")
    log_lines = [generate_log_line(i) for i in range(batch_start, min(batch_start + batch_size, total_logs))]
    df_raw = spark.createDataFrame([(line,) for line in log_lines], ["raw"])

    df_parsed = df_raw.select(
        regexp_extract("raw", log_pattern, 1).alias("ip_address"),
        regexp_extract("raw", log_pattern, 2).alias("timestamp_str"),
        regexp_extract("raw", log_pattern, 3).alias("method"),
        regexp_extract("raw", log_pattern, 4).alias("endpoint"),
        regexp_extract("raw", log_pattern, 5).alias("protocol"),
        regexp_extract("raw", log_pattern, 6).alias("status_code"),
        regexp_extract("raw", log_pattern, 7).alias("bytes"),
        regexp_extract("raw", log_pattern, 8).alias("user_agent")
    ).withColumn("timestamp", to_timestamp("timestamp_str", "dd/MMM/yyyy:HH:mm:ss Z")) \
     .drop("timestamp_str")

    df_parsed.writeTo("granica.granica_logs").using("iceberg").append()
    print(f"batch {batch_start} written")

spark.stop()
