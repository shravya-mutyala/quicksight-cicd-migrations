import json
import os
import time
import uuid
import urllib.request
import urllib.error
import boto3

QS_REGION      = os.environ.get("QS_REGION", "us-east-1")
TARGET_BUCKET  = os.environ["TARGET_BUCKET"]
TARGET_PREFIX  = os.environ.get("TARGET_PREFIX", "bundles/")
ALLOWED_FOLDER_IDS = set(
    x.strip() for x in os.environ.get("ALLOWED_FOLDER_IDS", "").split(",") if x.strip()
)

qs = boto3.client("quicksight", region_name=QS_REGION)
s3 = boto3.client("s3")

def poll_export(account_id, job_id, sleep=3, max_wait=600):
    start = time.time()
    while True:
        resp = qs.describe_asset_bundle_export_job(
            AwsAccountId=account_id,
            AssetBundleExportJobId=job_id
        )
        status = resp.get("JobStatus")
        if status in ("SUCCESSFUL", "FAILED"):
            return resp
        if time.time() - start > max_wait:
            raise TimeoutError(f"Export job {job_id} timed out with status={status}")
        time.sleep(sleep)

def get_folder_id(evt):
    detail = evt.get("detail", {})
    fid = detail.get("folderId")
    if isinstance(fid, list):
        return fid[0] if fid else None
    return fid

def list_folder_member_arns(account_id, folder_id):
    arns, token = [], None
    while True:
        kwargs = {
            "AwsAccountId": account_id,
            "FolderId": folder_id,
            "MaxResults": 100,
        }
        if token:
            kwargs["NextToken"] = token
        resp = qs.list_folder_members(**kwargs)
        for m in resp.get("FolderMemberList", []):
            arn = m.get("MemberArn")
            if arn:
                arns.append(arn)
        token = resp.get("NextToken")
        if not token:
            break
    return sorted(set(arns))

def arn_from_event(evt, region):
    res = evt.get("resources") or []
    if res:
        return res
    detail = evt.get("detail", {})
    account = evt.get("account")
    if not account:
        return []
    if "dashboardId" in detail:
        return [f"arn:aws:quicksight:{region}:{account}:dashboard/{detail['dashboardId']}"]
    if "analysisId" in detail:
        return [f"arn:aws:quicksight:{region}:{account}:analysis/{detail['analysisId']}"]
    if "datasetId" in detail or "dataSetId" in detail:
        dsid = detail.get("datasetId") or detail.get("dataSetId")
        return [f"arn:aws:quicksight:{region}:{account}:dataset/{dsid}"]
    return []

def lambda_handler(event, context):
    src_account = event["account"]

    folder_id = get_folder_id(event)
    if folder_id:
        if ALLOWED_FOLDER_IDS and folder_id not in ALLOWED_FOLDER_IDS:
            return {"status": "SKIPPED", "reason": "Folder not allowed", "folderId": folder_id}
        resource_arns = list_folder_member_arns(src_account, folder_id)
        if not resource_arns:
            return {"status": "SKIPPED", "reason": "Folder is empty", "folderId": folder_id}
    else:
        resource_arns = arn_from_event(event, QS_REGION)
        if not resource_arns:
            raise RuntimeError(f"Could not determine resources from event: {json.dumps(event)}")

    job_id = f"exp-{uuid.uuid4().hex[:12]}"
    qs.start_asset_bundle_export_job(
        AwsAccountId=src_account,
        AssetBundleExportJobId=job_id,
        ResourceArns=resource_arns,
        ExportFormat="QUICKSIGHT_JSON",
        IncludeAllDependencies=True,
        IncludePermissions=False,
        IncludeTags=True,
    )

    final = poll_export(src_account, job_id)
    if final.get("JobStatus") != "SUCCESSFUL":
        raise RuntimeError(f"Export failed: {json.dumps(final)}")

    final = qs.describe_asset_bundle_export_job(
        AwsAccountId=src_account,
        AssetBundleExportJobId=job_id
    )
    download_url = final.get("DownloadUrl")
    if not download_url:
        raise RuntimeError("No DownloadUrl on successful export job")

    try:
        bundle_bytes = urllib.request.urlopen(download_url, timeout=60).read()
    except urllib.error.URLError as e:
        raise RuntimeError(f"Failed to download bundle: {e}") from e

    key = f"{TARGET_PREFIX}{job_id}.qs"
    s3.put_object(Bucket=TARGET_BUCKET, Key=key, Body=bundle_bytes)

    return {
        "status": "OK",
        "job_status": final["JobStatus"],
        "folderId": folder_id,
        "resource_count": len(resource_arns),
        "s3_uri": f"s3://{TARGET_BUCKET}/{key}"
    }
