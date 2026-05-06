#!/usr/bin/env python3
import aws_cdk as cdk
from stacks.marketing_ai_stack import MarketingAiStack

app = cdk.App()

MarketingAiStack(
    app,
    "MarketingAiStack",
    env=cdk.Environment(
        account=app.node.try_get_context("account"),
        region=app.node.try_get_context("region") or "us-east-1",
    ),
    description="Marketing AI — Generación de imágenes y edición de contenido con Amazon Bedrock",
)

app.synth()
