#!/usr/bin/env python3
import aws_cdk as cdk
from src.config.load import load_config
from src.stacks.infra_stack import InfraStack

app = cdk.App()

cfg = load_config(app)

InfraStack(
    app,
    cfg["stackName"],
    cfg=cfg,
    env=cdk.Environment(
        account=cfg.get("awsAccount"),
        region=cfg.get("awsRegion"),
    ),
)

app.synth()
