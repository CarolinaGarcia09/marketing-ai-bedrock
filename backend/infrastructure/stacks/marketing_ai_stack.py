import aws_cdk as cdk
from aws_cdk import (
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_cognito as cognito,
    aws_iam as iam,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    Duration,
    RemovalPolicy,
    CfnOutput,
)
from constructs import Construct


class MarketingAiStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # ── S3: Imágenes generadas ─────────────────────────────────────────
        images_bucket = s3.Bucket(
            self, "ImagesBucket",
            bucket_name="marketing-ai-images",
            encryption=s3.BucketEncryption.S3_MANAGED,  # AES-256
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteOldVersions",
                    noncurrent_version_expiration=Duration.days(90),
                )
            ],
        )

        # ── DynamoDB: Historial de texto ───────────────────────────────────
        history_table = dynamodb.Table(
            self, "TextHistory",
            table_name="TextHistory",
            partition_key=dynamodb.Attribute(name="document_id", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="version_id", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
            point_in_time_recovery=True,
        )

        # ── DynamoDB: Jobs asincrónicos ────────────────────────────────────
        jobs_table = dynamodb.Table(
            self, "Jobs",
            table_name="Jobs",
            partition_key=dynamodb.Attribute(name="job_id", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="ttl",
            removal_policy=RemovalPolicy.DESTROY,
        )

        # ── Cognito: Autenticación y roles ─────────────────────────────────
        user_pool = cognito.UserPool(
            self, "UserPool",
            user_pool_name="marketing-ai-users",
            self_sign_up_enabled=False,          # Solo usuarios invitados
            sign_in_aliases=cognito.SignInAliases(email=True),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True,
            ),
            mfa=cognito.Mfa.OPTIONAL,
            removal_policy=RemovalPolicy.RETAIN,
        )

        # Grupos de usuarios
        for group_name in ["Designers", "Writers", "Approvers"]:
            cognito.CfnUserPoolGroup(
                self, f"Group{group_name}",
                user_pool_id=user_pool.user_pool_id,
                group_name=group_name,
            )

        user_pool_client = user_pool.add_client(
            "WebClient",
            user_pool_client_name="marketing-ai-web",
            auth_flows=cognito.AuthFlow(user_password=True, user_srp=True),
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(implicit_code_grant=True),
                scopes=[cognito.OAuthScope.OPENID, cognito.OAuthScope.EMAIL, cognito.OAuthScope.PROFILE],
            ),
        )

        # ── IAM: Rol para Lambdas ──────────────────────────────────────────
        lambda_role = iam.Role(
            self, "LambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
            ],
        )

        # Permisos mínimos necesarios
        lambda_role.add_to_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=[
                f"arn:aws:bedrock:{self.region}::foundation-model/stability.stable-diffusion-xl-v1",
                f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
            ],
        ))
        images_bucket.grant_read_write(lambda_role)
        history_table.grant_read_write_data(lambda_role)
        jobs_table.grant_read_write_data(lambda_role)
        lambda_role.add_to_policy(iam.PolicyStatement(
            actions=["rekognition:DetectModerationLabels"],
            resources=["*"],
        ))

        # ── Lambda: Configuración base ─────────────────────────────────────
        common_lambda_props = dict(
            runtime=_lambda.Runtime.PYTHON_3_12,
            role=lambda_role,
            timeout=Duration.seconds(300),
            memory_size=512,
            environment={
                "IMAGES_BUCKET": images_bucket.bucket_name,
                "HISTORY_TABLE": history_table.table_name,
                "JOBS_TABLE": jobs_table.table_name,
                "REGION": self.region,
            },
        )

        fn_generate = _lambda.Function(
            self, "GenerateImage",
            function_name="marketing-ai-generate-image",
            code=_lambda.Code.from_asset("../lambdas/generate_image"),
            handler="handler.lambda_handler",
            **common_lambda_props,
        )

        fn_edit = _lambda.Function(
            self, "EditText",
            function_name="marketing-ai-edit-text",
            code=_lambda.Code.from_asset("../lambdas/edit_text"),
            handler="handler.lambda_handler",
            **common_lambda_props,
        )

        fn_status = _lambda.Function(
            self, "JobStatus",
            function_name="marketing-ai-job-status",
            code=_lambda.Code.from_asset("../lambdas/job_status"),
            handler="handler.lambda_handler",
            timeout=Duration.seconds(10),
            memory_size=128,
            role=lambda_role,
            environment={"JOBS_TABLE": jobs_table.table_name},
        )

        # ── API Gateway ────────────────────────────────────────────────────
        authorizer = apigw.CognitoUserPoolsAuthorizer(
            self, "CognitoAuthorizer",
            cognito_user_pools=[user_pool],
        )

        api = apigw.RestApi(
            self, "MarketingAiApi",
            rest_api_name="marketing-ai-api",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "Authorization"],
            ),
        )

        auth_method_options = apigw.MethodOptions(
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO,
        )

        # POST /generate-image
        generate_resource = api.root.add_resource("generate-image")
        generate_resource.add_method(
            "POST",
            apigw.LambdaIntegration(fn_generate),
            **auth_method_options.__dict__,
        )

        # POST /edit-text
        edit_resource = api.root.add_resource("edit-text")
        edit_resource.add_method(
            "POST",
            apigw.LambdaIntegration(fn_edit),
            **auth_method_options.__dict__,
        )

        # GET /job-status/{job_id}
        job_resource = api.root.add_resource("job-status")
        job_id_resource = job_resource.add_resource("{job_id}")
        job_id_resource.add_method(
            "GET",
            apigw.LambdaIntegration(fn_status),
            **auth_method_options.__dict__,
        )

        # ── CloudFront para el frontend ────────────────────────────────────
        frontend_bucket = s3.Bucket(
            self, "FrontendBucket",
            bucket_name=f"marketing-ai-frontend-{self.account}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        distribution = cloudfront.Distribution(
            self, "FrontendDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(frontend_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
            default_root_object="index.html",
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                )
            ],
        )

        # ── Outputs ────────────────────────────────────────────────────────
        CfnOutput(self, "ApiUrl", value=api.url, description="URL de la API REST")
        CfnOutput(self, "UserPoolId", value=user_pool.user_pool_id)
        CfnOutput(self, "UserPoolClientId", value=user_pool_client.user_pool_client_id)
        CfnOutput(self, "FrontendUrl", value=f"https://{distribution.domain_name}")
        CfnOutput(self, "ImagesBucket", value=images_bucket.bucket_name)
