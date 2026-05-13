from pyspark.sql import SparkSession
import os

def get_spark(app_name: str = None, tz: str = "America/New_York"):
    """
    Create or get an existing SparkSession with common configs.

    Parameters
    ----------
    app_name : str, optional
        Name of the Spark application. Defaults to NB_NAME env var
        if available, otherwise "MAST30034".
    tz : str, optional
        Timezone for Spark SQL session. Defaults to "America/New_York"
        (local time for NYC datasets).
    """
    app = app_name or  "MAST30034"

    spark = (
        SparkSession.builder
        .appName(app)
        .config("spark.sql.repl.eagerEval.enabled", True)   # notebook-friendly previews
        .config("spark.sql.parquet.cacheMetadata", "true")  # speed up parquet schema reads
        .config("spark.sql.session.timeZone", tz)           # ensure timestamps align to NYC local time
        .config("spark.sql.shuffle.partitions", "64")       # tune for laptop (default 200 is often too high)
        .getOrCreate()
    )

    return spark
