#!/usr/bin/env python
import aws_cdk as cdk
from src.config.load import load_config
from src.stacks.infra_stack import InfraStack
from src.stacks.target_stack import TargetStack

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

# -------- Target env (S3 bucket + Lambda) --------
target_cfg = cfg.get("target")
if target_cfg:
    target_env = cdk.Environment(
        account=target_cfg.get("awsAccount"),
        region=target_cfg.get("awsRegion"),
    )

    TargetStack(
        app,
        f'{cfg["stackName"]}-target',
        env=target_env,
        bucket_name=target_cfg["bucket"]["name"],
        versioned=target_cfg["bucket"].get("versioned", True),
        source_put_principal_arn=target_cfg.get("sourcePutPrincipalArn"),
        target_prefix=cfg.get("lambda", {}).get("targetPrefix", "bundles/"),
        allow_put_object_acl=bool(target_cfg.get("allowPutObjectAcl", False)),
        target_account=target_cfg["awsAccount"],
        qs_region=cfg["awsRegion"],
        lambda_timeout=target_cfg.get("lambda", {}).get("timeout", 60),
        lambda_memory=target_cfg.get("lambda", {}).get("memory", 128),
    )

app.synth()

