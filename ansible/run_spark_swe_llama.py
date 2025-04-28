import argparse
import json
import os
import pandas as pd
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, pandas_udf, udf
from pyspark.sql.types import StringType
import time

# --- Model Parameters ---
DEFAULT_MODEL_PATH = "/opt/models/swe-llama-7b"
MAX_NEW_TOKENS = 512
TEMPERATURE = 0.2
TOP_P = 0.95
NUM_RETURN_SEQUENCES = 1

# --- UDF Definitions (generate_fix_udf, format_prompt_udf) ---
# (Keep the UDF definitions exactly as they were in the previous version)
# ... (generate_fix_udf definition) ...
# ... (format_prompt definition) ...
# ... (format_prompt_udf definition) ...

@pandas_udf(StringType())
def generate_fix_udf(prompts: pd.Series) -> pd.Series:
    # --- Load Model inside UDF ---
    model_path = os.environ.get("MODEL_PATH_FOR_UDF", DEFAULT_MODEL_PATH)

    _tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    if _tokenizer.pad_token is None:
        _tokenizer.pad_token = _tokenizer.eos_token

    _model = AutoModelForCausalLM.from_pretrained(
        model_path,
        device_map="cpu",
        torch_dtype=torch.float32,
        trust_remote_code=True
    )
    _model.eval()

    results = []
    with torch.no_grad():
        for prompt in prompts:
            if not prompt:
                results.append(None)
                continue
            try:
                inputs = _tokenizer(prompt, return_tensors="pt")
                outputs = _model.generate(
                    inputs.input_ids,
                    max_new_tokens=MAX_NEW_TOKENS,
                    temperature=TEMPERATURE,
                    top_p=TOP_P,
                    num_return_sequences=NUM_RETURN_SEQUENCES,
                    pad_token_id=_tokenizer.eos_token_id
                )
                prompt_len = inputs.input_ids.shape[1]
                decoded_output = _tokenizer.decode(outputs[0, prompt_len:], skip_special_tokens=True)
                cleaned_output = decoded_output.strip()
                if cleaned_output.startswith("```python"):
                     cleaned_output = cleaned_output[len("```python"):].strip()
                if cleaned_output.endswith("```"):
                     cleaned_output = cleaned_output[:-len("```")].strip()
                results.append(cleaned_output)
            except Exception as e:
                print(f"Error during generation for one prompt: {e}")
                results.append(f"Error: {e}")
    return pd.Series(results)

def format_prompt(problem_statement):
    return f"""INSTRUCTION: You are an expert programmer. Rewrite the following code snippet to fix the bug described or inferred from the issue description. Only output the complete fixed code snippet.

PROBLEM:
{problem_statement}

FIXED CODE:
```python
"""

format_prompt_udf = udf(format_prompt, StringType())
# --- End UDF Definitions ---


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run SWE-Llama inference on SWE-Bench using Spark, save to MinIO.")
    # --- Existing Args ---
    parser.add_argument("--dataset_path", required=True, help="Path to the downloaded SWE-Bench dataset repository root directory (e.g., /opt/data/swe-bench-full).")
    parser.add_argument("--dataset_split", default="test", choices=["train", "dev", "test"], help="Which split to process (train, dev, test).")
    parser.add_argument("--model_path_override", default=DEFAULT_MODEL_PATH, help=f"Override default model path ({DEFAULT_MODEL_PATH}) if needed.")
    # --- New MinIO Args ---
    parser.add_argument("--minio_endpoint", required=True, help="MinIO server endpoint URL (e.g., http://<minio_ip>:9000).")
    parser.add_argument("--minio_access_key", required=True, help="MinIO access key.")
    parser.add_argument("--minio_secret_key", required=True, help="MinIO secret key.")
    parser.add_argument("--minio_bucket", required=True, help="MinIO bucket name to save results in.")
    parser.add_argument("--output_path_prefix", default="swe_llama_results", help="Prefix for the output path within the MinIO bucket.")

    args = parser.parse_args()

    # Set environment variable for the UDF to access the potentially overridden model path
    os.environ["MODEL_PATH_FOR_UDF"] = args.model_path_override

    # --- Configure SparkSession for S3A ---
    spark_builder = SparkSession.builder.appName("SWE_Llama_Inference_MinIO")

    # S3A Configuration (adjust http/https and path style as needed for your MinIO setup)
    spark_builder.config("spark.hadoop.fs.s3a.endpoint", args.minio_endpoint)
    spark_builder.config("spark.hadoop.fs.s3a.access.key", args.minio_access_key)
    spark_builder.config("spark.hadoop.fs.s3a.secret.key", args.minio_secret_key)
    spark_builder.config("spark.hadoop.fs.s3a.path.style.access", "true") # Usually true for MinIO
    spark_builder.config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") # Set to true if MinIO uses HTTPS
    spark_builder.config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
    # Optional: Recommended committer for S3A
    # spark_builder.config("spark.sql.parquet.output.committer.class", "org.apache.hadoop.mapreduce.lib.output.BindingParquetOutputCommitter")

    spark = spark_builder.getOrCreate()
    # --- End S3A Configuration ---

    sc = spark.sparkContext
    print(f"Spark Application ID: {sc.applicationId}")
    print(f"Using Model Path: {args.model_path_override}")
    print(f"Processing Dataset: {args.dataset_path}, Split: {args.dataset_split}")
    print(f"MinIO Endpoint: {args.minio_endpoint}")
    print(f"MinIO Bucket: {args.minio_bucket}")

    # --- Load Dataset (Same as before) ---
    parquet_path_pattern = os.path.join(args.dataset_path, "data", f"{args.dataset_split}*.parquet")
    read_path = f"file://{parquet_path_pattern}"
    print(f"Attempting to read Parquet files from: {read_path}")
    try:
        df = spark.read.parquet(read_path)
        required_cols = ["instance_id", "problem_statement"]
        if not all(col in df.columns for col in required_cols):
             missing_cols = [col for col in required_cols if col not in df.columns]
             raise ValueError(f"Dataset is missing required columns: {missing_cols}. Found columns: {df.columns}")
        print("Dataset loaded successfully.")
        # df.select(required_cols).show(5, truncate=80) # Optional show
    except Exception as e:
        print(f"Error loading dataset from Parquet path {read_path}: {e}")
        spark.stop()
        exit(1)

    # --- Prepare Data and Apply UDF (Same as before) ---
    df_with_prompt = df.withColumn("prompt", format_prompt_udf(col("problem_statement")))
    df_to_process = df_with_prompt.select("instance_id", "prompt").dropna(subset=["prompt"])
    instance_count = df_to_process.count()
    if instance_count == 0:
        print("No instances found to process after filtering. Exiting.")
        spark.stop()
        exit(0)
    print(f"Processing {instance_count} instances...")

    print("Applying model UDF...")
    start_time = time.time()
    result_df = df_to_process.withColumn("generated_fix", generate_fix_udf(col("prompt")))
    end_time = time.time()
    print(f"Model UDF application finished in {end_time - start_time:.2f} seconds ({instance_count} instances).")

    # --- Save Results to MinIO ---
    output_s3_path = f"s3a://{args.minio_bucket}/{args.output_path_prefix}_{args.dataset_split}"
    print(f"Saving results to MinIO path: {output_s3_path}")
    try:
        result_df.select("instance_id", "prompt", "generated_fix") \
            .write.mode("overwrite").parquet(output_s3_path)
        print("Results successfully saved to MinIO.")
    except Exception as e:
        print(f"ERROR saving results to MinIO: {e}")
        # Potentially add more detailed error logging or handling here

    print("Processing complete.")
    spark.stop()