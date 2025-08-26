from constructs import Construct
from aws_cdk import Stack, CfnOutput
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from src.cdk_construct.backend_construct import BackendConstruct

class InfraStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, cfg: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        backend = BackendConstruct(self, "Backend", cfg=cfg)

        # --- EventBridge rule (folder membership updates) ---
        # Pull folder IDs from cfg["lambda"]["allowedFolderIds"] if present.
        allowed_ids = (cfg.get("lambda", {}).get("allowedFolderIds") or "").split(",")
        allowed_ids = [x.strip() for x in allowed_ids if x.strip()]

        # Build event pattern; only include the folderId filter if you have any
        event_pattern = events.EventPattern(
            source=["aws.quicksight"],
            detail_type=["QuickSight Folder Membership Updated"],
            # detail filter is optional—omit if no IDs provided
            detail={"folderId": allowed_ids} if allowed_ids else None,
        )

        rule = events.Rule(
            self,
            "QsFolderMembershipUpdatedRule",
            event_pattern=event_pattern,
            enabled=True,  # default True, explicit for clarity
        )
        rule.add_target(targets.LambdaFunction(backend.func))

        # (Optional) legacy update events (dashboard/analysis/dataset)
        if cfg.get("lambda", {}).get("enableLegacyEvents"):
            legacy_rule = events.Rule(
                self,
                "QsLegacyUpdateRule",
                event_pattern=events.EventPattern(
                    source=["aws.quicksight"],
                    detail_type=[
                        "QuickSight Dashboard Updated",
                        "QuickSight Analysis Updated",
                        "QuickSight DataSet Updated",
                        "Quicksight Folder Membership Updated",  # included for completeness
                    ],
                ),
                enabled=True,
            )
            legacy_rule.add_target(targets.LambdaFunction(backend.func))

        # Outputs
        CfnOutput(self, "BucketNameOut", value=backend.bucket.bucket_name)
        CfnOutput(self, "BucketArnOut", value=backend.bucket.bucket_arn)
        CfnOutput(self, "LambdaNameOut", value=backend.func.function_name)
        CfnOutput(self, "LambdaArnOut", value=backend.func.function_arn)
