from constructs import Construct
from aws_cdk import (
    Duration,
    aws_lambda as _lambda,
    aws_s3 as s3,
    aws_iam as iam,
)

RUNTIME_MAP = {
    "python3.12": _lambda.Runtime.PYTHON_3_12,
    "python3.11": _lambda.Runtime.PYTHON_3_11,
    "python3.10": _lambda.Runtime.PYTHON_3_10,
    "python3.9":  _lambda.Runtime.PYTHON_3_9,
}

class BackendConstruct(Construct):
    def __init__(self, scope: Construct, id: str, *, cfg: dict) -> None:
        super().__init__(scope, id)

        bucket_cfg = cfg.get("bucket", {})
        lambda_cfg = cfg.get("lambda", {})
        target_bucket_cfg = cfg.get("targetBucket", {})

        # Primary S3 bucket
        self.bucket = s3.Bucket(
            self, "AppBucket",
            bucket_name=bucket_cfg.get("name") or None,
            versioned=bucket_cfg.get("versioned", True),
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
        )

        # Optional separate target bucket
        self.target_bucket = None
        if target_bucket_cfg:
            self.target_bucket = s3.Bucket(
                self, "TargetBucket",
                bucket_name=target_bucket_cfg.get("name") or None,
                versioned=target_bucket_cfg.get("versioned", True),
                block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
                encryption=s3.BucketEncryption.S3_MANAGED,
                enforce_ssl=True,
            )

        target_bucket_name = (
            self.target_bucket.bucket_name if self.target_bucket else self.bucket.bucket_name
        )

        # Resolve runtime enum safely
        cfg_runtime = (lambda_cfg.get("runtime") or "python3.12").lower()
        runtime_enum = RUNTIME_MAP.get(cfg_runtime)
        if runtime_enum is None:
            raise ValueError(f"Unsupported runtime '{cfg_runtime}'. Choose one of: {list(RUNTIME_MAP.keys())}")

        # Lambda
        self.func = _lambda.Function(
            self, "MyLambda",
            function_name=lambda_cfg.get("functionName"),
            runtime=runtime_enum,  # <-- enum, not string
            handler=lambda_cfg.get("handler", "index.lambda_handler"),
            code=_lambda.Code.from_asset(lambda_cfg.get("codePath", "lambda_src/handler")),
            timeout=Duration.seconds(lambda_cfg.get("timeout", 60)),
            memory_size=lambda_cfg.get("memory", 1024),
            environment={
                "BUCKET_NAME": self.bucket.bucket_name,           # legacy var (ok)
                "QS_REGION": lambda_cfg.get("qsRegion", "us-east-1"),
                "TARGET_BUCKET": target_bucket_name,              # <-- use chosen target bucket
                "TARGET_PREFIX": lambda_cfg.get("targetPrefix", "bundles/"),
                "ALLOWED_FOLDER_IDS": lambda_cfg.get("allowedFolderIds", ""),
            },
        )

        # QuickSight perms
        self.func.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "quicksight:StartAssetBundleExportJob",
                    "quicksight:DescribeAssetBundleExportJob",
                    "quicksight:ListFolderMembers",
                    "quicksight:DescribeDashboard",
                    "quicksight:DescribeAnalysis",
                    "quicksight:DescribeDataSet",
                    "quicksight:DescribeTheme",
                    "quicksight:DescribeTopic",
                    "quicksight:ListDashboards",
                    "quicksight:ListAnalyses",
                    "quicksight:ListDataSets",
                    "quicksight:ListThemes",
                    "quicksight:ListTopics",
                ],
                resources=["*"],
            )
        )

        # S3 access
        self.bucket.grant_read_write(self.func)
        if self.target_bucket:
            self.target_bucket.grant_read_write(self.func)
