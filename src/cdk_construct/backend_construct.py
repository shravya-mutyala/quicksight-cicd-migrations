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

        bucket_cfg = cfg.get("bucket", {}) or {}
        lambda_cfg = cfg.get("lambda", {}) or {}

        # ---- read target bucket name (supports both config styles) ----
        target_bucket_name = None
        if cfg.get("target") and cfg["target"].get("bucket", {}).get("name"):
            target_bucket_name = cfg["target"]["bucket"]["name"]
        elif cfg.get("targetBucket", {}).get("name"):
            target_bucket_name = cfg["targetBucket"]["name"]

        # Optional: also allow PutObjectAcl if the source sets ACLs (used by target stack)
        allow_put_object_acl: bool = bool(cfg.get("allowPutObjectAcl", False))

        # S3 object prefix for exported bundles (normalize to trailing slash)
        target_prefix: str = (lambda_cfg.get("targetPrefix", "bundles/") or "bundles/").lstrip("/")
        if not target_prefix.endswith("/"):
            target_prefix += "/"

        # ---------------------------------------------------------------------
        # Primary S3 bucket (SOURCE account)
        # ---------------------------------------------------------------------
        self.bucket = s3.Bucket(
            self, "AppBucket",
            bucket_name=bucket_cfg.get("name") or None,
            versioned=bucket_cfg.get("versioned", True),
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
        )

        # ---------------------------------------------------------------------
        # Resolve runtime enum safely
        # ---------------------------------------------------------------------
        cfg_runtime = (lambda_cfg.get("runtime") or "python3.12").lower()
        runtime_enum = RUNTIME_MAP.get(cfg_runtime)
        if runtime_enum is None:
            raise ValueError(f"Unsupported runtime '{cfg_runtime}'. Choose one of: {list(RUNTIME_MAP.keys())}")

        # ---------------------------------------------------------------------
        # Lambda (SOURCE account)
        # ---------------------------------------------------------------------
        self.func = _lambda.Function(
            self, "MyLambda",
            function_name=lambda_cfg.get("functionName"),
            runtime=runtime_enum,
            handler=lambda_cfg.get("handler", "index.lambda_handler"),
            code=_lambda.Code.from_asset(lambda_cfg.get("codePath", "lambda_src/handler")),
            timeout=Duration.seconds(lambda_cfg.get("timeout", 60)),
            memory_size=lambda_cfg.get("memory", 1024),
            environment={
                "BUCKET_NAME": self.bucket.bucket_name,  # legacy var (ok)
                "QS_REGION": lambda_cfg.get("qsRegion", "us-east-1"),
                # If no target bucket configured, fall back to source bucket
                "TARGET_BUCKET": target_bucket_name or self.bucket.bucket_name,
                "TARGET_PREFIX": target_prefix,
                "ALLOWED_FOLDER_IDS": lambda_cfg.get("allowedFolderIds", ""),
            },
        )

        # ---------------------------------------------------------------------
        # Permissions for this Lambda
        # ---------------------------------------------------------------------
        # 1) RW on the primary/source bucket
        self.bucket.grant_read_write(self.func)

        # 2) If a target bucket name is configured (cross-account safe):
        #    give the Lambda principal permission to PutObject to that bucket/prefix.
        if target_bucket_name:
            self.func.add_to_role_policy(
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["s3:PutObject"],
                    resources=[f"arn:aws:s3:::{target_bucket_name}/{target_prefix}*"],
                )
            )

        # NOTE:
        # Cross-account *bucket* side permission is handled by the TargetBucketStack
        # via a bucket resource policy (principal = source lambda exec role).
