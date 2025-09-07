import json
import os
import time
import uuid
import boto3

QS_REGION       = os.environ.get("QS_REGION", "us-east-1")
TARGET_ACCOUNT  = os.environ["TARGET_ACCOUNT"]
OVERRIDES_S3_KEY = os.environ.get("OVERRIDES_S3_KEY")

qs = boto3.client("quicksight", region_name=QS_REGION)
s3 = boto3.client("s3")

def poll_import(job_id, sleep=3, max_wait=900):
    """Polls describe_asset_bundle_import_job until JobStatus is terminal."""
    start = time.time()
    while True:
        resp = qs.describe_asset_bundle_import_job(
            AwsAccountId=TARGET_ACCOUNT,
            AssetBundleImportJobId=job_id
        )
        status = resp.get("JobStatus")  # <-- top-level field
        if status in ("SUCCESSFUL", "FAILED", "FAILED_ROLLBACK_COMPLETED", "FAILED_ROLLBACK_ERROR"):
            return resp
        if time.time() - start > max_wait:
            raise TimeoutError(f"Import job {job_id} timed out with status={status}")
        time.sleep(sleep)

def lambda_handler(event, context):
    # ----- S3 event parsing (use Records[0] for both bucket and key) -----
    rec = event["Records"][0]
    bucket = rec["s3"]["bucket"]["name"]
    key    = rec["s3"]["object"]["key"]
    s3_uri = f"s3://{bucket}/{key}"

    # ----- Optional: load overrides JSON from the same bucket -----
    override_params = {}
    try:
        if OVERRIDES_S3_KEY:
            obj = s3.get_object(Bucket=bucket, Key=OVERRIDES_S3_KEY)
            override_params = json.loads(obj["Body"].read()).get("OverrideParameters", {})
    except Exception as e:
        # Proceed without overrides; log and continue
        print(f"[WARN] Could not load overrides at s3://{bucket}/{OVERRIDES_S3_KEY}: {e}")

    # ----- Start import job (FailureAction=ROLLBACK is safer) -----
    job_id = f"imp-{uuid.uuid4().hex[:12]}"
    start_resp = qs.start_asset_bundle_import_job(
        AwsAccountId=TARGET_ACCOUNT,
        AssetBundleImportJobId=job_id,
        AssetBundleImportSource={"S3Uri": s3_uri},
        FailureAction="ROLLBACK",
        OverrideParameters=override_params
    )
    print(f"[INFO] Started import job {job_id} for {s3_uri}: {json.dumps(start_resp, default=str)}")

    # ----- Poll until terminal status -----
    final = poll_import(job_id)
    status = final.get("JobStatus")
    print(f"[INFO] Import job {job_id} final status: {status}")
    if status != "SUCCESSFUL":
        # Surface errors/warnings clearly in logs
        raise RuntimeError(json.dumps({
            "status": status,
            "errors": final.get("Errors"),
            "rollbackErrors": final.get("RollbackErrors"),
            "warnings": final.get("Warnings")
        }, default=str))

    return {"status": "OK", "import_job": job_id, "s3_uri": s3_uri}
