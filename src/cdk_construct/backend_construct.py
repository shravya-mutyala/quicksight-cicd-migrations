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

        # Extract configuration sections
        self.bucket_cfg = cfg.get("bucket", {}) or {}
        self.lambda_cfg = cfg.get("lambda", {}) or {}
        
        # Parse target configuration
        self.target_bucket_name = self._get_target_bucket_name(cfg)
        self.allow_put_object_acl = bool(cfg.get("allowPutObjectAcl", False))
        self.target_prefix = self._normalize_prefix(
            self.lambda_cfg.get("targetPrefix", "bundles/")
        )

        # Create resources
        self.bucket = self._create_source_bucket()
        self.func = self._create_source_lambda()
        
        # Configure permissions
        self._configure_permissions()

    def _get_target_bucket_name(self, cfg: dict) -> str | None:
        """Extract target bucket name from configuration (supports multiple formats)."""
        if cfg.get("target") and cfg["target"].get("bucket", {}).get("name"):
            return cfg["target"]["bucket"]["name"]
        elif cfg.get("targetBucket", {}).get("name"):
            return cfg["targetBucket"]["name"]
        return None

    def _normalize_prefix(self, prefix: str) -> str:
        """Normalize S3 prefix to ensure consistent format."""
        normalized = (prefix or "bundles/").lstrip("/")
        return normalized if normalized.endswith("/") else f"{normalized}/"

    def _resolve_runtime(self) -> _lambda.Runtime:
        """Resolve Lambda runtime from configuration."""
        cfg_runtime = (self.lambda_cfg.get("runtime") or "python3.12").lower()
        runtime_enum = RUNTIME_MAP.get(cfg_runtime)
        if runtime_enum is None:
            raise ValueError(
                f"Unsupported runtime '{cfg_runtime}'. "
                f"Choose one of: {list(RUNTIME_MAP.keys())}"
            )
        return runtime_enum

    def _create_source_bucket(self) -> s3.Bucket:
        """Create the primary S3 bucket in the source account."""
        return s3.Bucket(
            self, "AppBucket",
            bucket_name=self.bucket_cfg.get("name") or None,
            versioned=self.bucket_cfg.get("versioned", True),
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
        )

    def _create_source_lambda(self) -> _lambda.Function:
        """Create the source Lambda function with proper configuration."""
        return _lambda.Function(
            self, "MyLambda",
            function_name=self.lambda_cfg.get("functionName"),
            runtime=self._resolve_runtime(),
            handler=self.lambda_cfg.get("handler", "index.lambda_handler"),
            code=_lambda.Code.from_asset(
                self.lambda_cfg.get("codePath", "lambda_src/handler")
            ),
            timeout=Duration.seconds(self.lambda_cfg.get("timeout", 60)),
            memory_size=self.lambda_cfg.get("memory", 1024),
            environment=self._build_environment_variables(),
        )

    def _build_environment_variables(self) -> dict[str, str]:
        """Build environment variables for the Lambda function."""
        return {
            "BUCKET_NAME": self.bucket.bucket_name,
            "QS_REGION": self.lambda_cfg.get("qsRegion", "us-east-1"),
            "TARGET_BUCKET": self.target_bucket_name or self.bucket.bucket_name,
            "TARGET_PREFIX": self.target_prefix,
            "ALLOWED_FOLDER_IDS": self.lambda_cfg.get("allowedFolderIds", ""),
        }

    def _configure_permissions(self) -> None:
        """Configure all necessary permissions for the Lambda function."""
        # Grant read/write permissions on the source bucket
        self.bucket.grant_read_write(self.func)
        
        # Configure cross-account permissions if target bucket is specified
        if self.target_bucket_name:
            self._configure_cross_account_permissions()

    def _configure_cross_account_permissions(self) -> None:
        """Configure cross-account permissions for target bucket access."""
        actions = ["s3:PutObject"]
        if self.allow_put_object_acl:
            actions.append("s3:PutObjectAcl")
            
        self.func.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=actions,
                resources=[
                    f"arn:aws:s3:::{self.target_bucket_name}/{self.target_prefix}*"
                ],
            )
        )
