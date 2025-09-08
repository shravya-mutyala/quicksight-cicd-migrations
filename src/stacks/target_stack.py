from aws_cdk import (
    Stack,
    Duration,
    CfnOutput,
    aws_s3 as s3,
    aws_iam as iam,
    aws_lambda as _lambda,
)
from constructs import Construct

class TargetStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        bucket_name: str,
        versioned: bool = True,
        source_put_principal_arn: str | None = None,
        target_prefix: str = "bundles/",
        allow_put_object_acl: bool = False,
        target_account: str,
        qs_region: str,
        lambda_timeout: int = 60,
        lambda_memory: int = 128,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Normalize prefix to ensure consistent format
        self.target_prefix = self._normalize_prefix(target_prefix)

        # Create the S3 bucket in the TARGET account
        self.target_bucket = self._create_target_bucket(bucket_name, versioned)
        
        # Configure cross-account permissions for source Lambda
        if source_put_principal_arn:
            self._configure_cross_account_permissions(
                source_put_principal_arn, 
                allow_put_object_acl
            )

        # Create the target Lambda function
        self.target_function = self._create_target_lambda(
            target_account, 
            qs_region, 
            lambda_timeout, 
            lambda_memory
        )
        
        # Configure Lambda permissions
        self._configure_lambda_permissions()
        
        # Create stack outputs
        self._create_outputs()

    def _normalize_prefix(self, prefix: str) -> str:
        """Normalize S3 prefix to ensure consistent format."""
        normalized = (prefix or "bundles/").lstrip("/")
        return normalized if normalized.endswith("/") else f"{normalized}/"

    def _create_target_bucket(self, bucket_name: str, versioned: bool) -> s3.Bucket:
        """Create the target S3 bucket with security best practices."""
        return s3.Bucket(
            self, "TargetBucket",
            bucket_name=bucket_name,
            versioned=versioned,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
        )

    def _configure_cross_account_permissions(
        self, 
        source_principal_arn: str, 
        allow_put_object_acl: bool
    ) -> None:
        """Configure cross-account permissions for source Lambda."""
        actions = ["s3:PutObject"]
        if allow_put_object_acl:
            actions.append("s3:PutObjectAcl")

        self.target_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowSourceLambdaToPut",
                effect=iam.Effect.ALLOW,
                principals=[iam.ArnPrincipal(source_principal_arn)],
                actions=actions,
                resources=[self.target_bucket.arn_for_objects(f"{self.target_prefix}*")],
            )
        )

    def _create_target_lambda(
        self, 
        target_account: str, 
        qs_region: str, 
        timeout: int, 
        memory: int
    ) -> _lambda.Function:
        """Create the target Lambda function with optimized configuration."""
        return _lambda.Function(
            self, "TargetWorkerFn",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=_lambda.Code.from_asset("lambda_src/target_worker"),
            timeout=Duration.seconds(timeout),
            memory_size=memory,
            environment={
                "BUCKET_NAME": self.target_bucket.bucket_name,
                "TARGET_ACCOUNT": str(target_account),
                "QS_REGION": str(qs_region),
                "TARGET_PREFIX": self.target_prefix,
            },
        )

    def _configure_lambda_permissions(self) -> None:
        """Configure Lambda permissions with least privilege principle."""
        self.target_bucket.grant_read(self.target_function)

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs for important resources."""
        CfnOutput(self, "TargetBucketName", value=self.target_bucket.bucket_name)
        CfnOutput(self, "TargetBucketArn", value=self.target_bucket.bucket_arn)
        CfnOutput(self, "TargetLambdaName", value=self.target_function.function_name)
        CfnOutput(self, "TargetLambdaArn", value=self.target_function.function_arn)
        CfnOutput(self, "TargetLambdaRoleArn", value=self.target_function.role.role_arn)