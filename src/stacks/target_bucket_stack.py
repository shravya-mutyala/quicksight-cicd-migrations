from aws_cdk import (
    Stack,
    CfnOutput,
    aws_s3 as s3,
    aws_iam as iam,
)
from constructs import Construct

class TargetBucketStack(Stack):
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
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # normalize prefix
        target_prefix = (target_prefix or "bundles/").lstrip("/")
        if not target_prefix.endswith("/"):
            target_prefix += "/"

        # Create the bucket in the TARGET account
        self.target_bucket = s3.Bucket(
            self, "TargetBucket",
            bucket_name=bucket_name,
            versioned=versioned,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
        )

        # Allow the *source lambda execution role* to PutObject to this bucket/prefix
        if source_put_principal_arn:
            actions = ["s3:PutObject"]
            if allow_put_object_acl:
                actions.append("s3:PutObjectAcl")

            self.target_bucket.add_to_resource_policy(
                iam.PolicyStatement(
                    sid="AllowSourceLambdaToPut",
                    effect=iam.Effect.ALLOW,
                    principals=[iam.ArnPrincipal(source_put_principal_arn)],
                    actions=actions,
                    resources=[self.target_bucket.arn_for_objects(f"{target_prefix}*")],
                )
            )

        CfnOutput(self, "TargetBucketName", value=self.target_bucket.bucket_name)
