from aws_cdk import (
    Stack, Duration,
    aws_lambda as _lambda,
    aws_s3 as s3,
)
from constructs import Construct

class TargetLambdaStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        bucket_name: str,
        target_account: str,   # ← add
        qs_region: str,        # ← add
        **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        bucket = s3.Bucket.from_bucket_name(self, "TargetBucket", bucket_name)

        target_fn = _lambda.Function(
            self, "TargetWorkerFn",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=_lambda.Code.from_asset("lambda_src/target_worker"),
            timeout=Duration.seconds(60),
            environment={
                "BUCKET_NAME": bucket.bucket_name,
                "TARGET_ACCOUNT": str(target_account),
                "QS_REGION": str(qs_region),
            },
        )

        bucket.grant_read_write(target_fn)
