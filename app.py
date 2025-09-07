#!/usr/bin/env python
import aws_cdk as cdk
from src.config.load import load_config
from src.stacks.infra_stack import InfraStack
from src.stacks.target_bucket_stack import TargetBucketStack
from src.stacks.target_lambda_stack import TargetLambdaStack

app = cdk.App()

cfg = load_config(app)

# -------- Source env (QuickSight + Lambda) --------
source_env = cdk.Environment(
    account=cfg.get("awsAccount"),
    region=cfg.get("awsRegion"),
)

InfraStack(
    app,
    cfg["stackName"],
    cfg=cfg,
    env=source_env,
)

# -------- Target env (S3 target bucket + policy) --------
target_cfg = cfg.get("target")
if target_cfg:
    target_env = cdk.Environment(
        account=target_cfg.get("awsAccount"),
        region=target_cfg.get("awsRegion"),
    )

    TargetBucketStack(
        app,
        f'{cfg["stackName"]}-target-bucket',
        env=target_env,
        bucket_name=target_cfg["bucket"]["name"],
        versioned=target_cfg["bucket"].get("versioned", True),
        source_put_principal_arn=target_cfg.get("sourcePutPrincipalArn"),
        target_prefix=cfg.get("lambda", {}).get("targetPrefix", "bundles/"),
        allow_put_object_acl=bool(target_cfg.get("allowPutObjectAcl", False)),
    )

    # NEW target lambda stack (uses same target_env & target_cfg)
    TargetLambdaStack(
        app,
        f'{cfg["stackName"]}-target-lambda',
        env=target_env,
        bucket_name=target_cfg["bucket"]["name"],
        target_account=target_cfg["awsAccount"],   # ← pass in
        qs_region=cfg["awsRegion"]
    )

app.synth()

