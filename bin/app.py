#!/usr/bin/env python3
import os
from aws_cdk import (
    App, Environment
)
from stacks.s3_stack import S3Stack
from stacks.iam_stack import IamStack
from stacks.lambda_stack import LambdaStack
from stacks.events_stack import EventsStack
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

# Ensure 'stacks' is in the path for module resolution
stacks_path = pathlib.Path(__file__).resolve().parents[1] / "stacks"
if str(stacks_path) not in sys.path:
    sys.path.insert(0, str(stacks_path))


app = App()

env = Environment(
    account=os.getenv("CDK_DEFAULT_ACCOUNT"),
    region=os.getenv("CDK_DEFAULT_REGION")
)

ctx = app.node.try_get_context
project = ctx("projectName") or "qs-cicd"
bucket_name = ctx("bucketName")
trusted_acct = ctx("trustedAccountId")
external_id = ctx("externalId") or ""

lambda_cfg = ctx("lambda") or {}
runtime = lambda_cfg.get("runtime", "python3.12")
handler = lambda_cfg.get("handler", "app.handler")
memory = int(lambda_cfg.get("memory", 256))
timeout = int(lambda_cfg.get("timeout", 30))

s3 = S3Stack(app, f"{project}-s3", env=env, project_name=project, bucket_name=bucket_name)

iam = IamStack(
    app, f"{project}-iam", env=env, project_name=project,
    app_bucket_arn=s3.bucket.bucket_arn,
    trusted_account_id=trusted_acct, external_id=external_id
)

lmb = LambdaStack(
    app, f"{project}-lambda", env=env, project_name=project,
    role=iam.lambda_exec_role, app_bucket=s3.bucket,
    runtime=runtime, handler=handler, memory=memory, timeout=timeout
)

EventsStack(app, f"{project}-events", env=env, project_name=project, fn=lmb.fn)

app.synth()
