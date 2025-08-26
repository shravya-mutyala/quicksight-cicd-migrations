import os
import json
import boto3

s3 = boto3.client("s3")
BUCKET = os.environ["BUCKET_NAME"]

def lambda_handler(event, context):
    # Example write to S3 to show perms work
    s3.put_object(
        Bucket=BUCKET,
        Key="hello-from-lambda.txt",
        Body=b"Hello from CDK Lambda!"
    )
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Success", "bucket": BUCKET})
    }
