import boto3
import base64
import json
import uuid
from datetime import datetime, timezone

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
rekognition = boto3.client("rekognition")

BUCKET = "marketing-ai-images"
JOBS_TABLE = dynamodb.Table("Jobs")

STYLE_MODIFIERS = {
    "realistic":   "photorealistic, high detail, 4k, professional photography",
    "anime":       "anime style, vibrant colors, studio ghibli inspired",
    "oil_painting":"oil painting, textured brushstrokes, classical art style",
    "sketch":      "pencil sketch, hand drawn, detailed linework",
    "minimalist":  "minimalist, clean lines, flat design, simple composition",
}

NEGATIVE_PROMPT = (
    "blurry, low quality, distorted, watermark, deformed, ugly, "
    "bad anatomy, bad proportions, duplicate, out of frame"
)


def is_prompt_safe(prompt: str) -> bool:
    """Filtra prompts con términos prohibidos."""
    forbidden = ["violence", "nsfw", "explicit", "hate", "weapon", "gore", "nude"]
    return not any(term in prompt.lower() for term in forbidden)


def is_image_safe(image_bytes: bytes) -> bool:
    """Retorna True si la imagen no contiene contenido inapropiado."""
    response = rekognition.detect_moderation_labels(
        Image={"Bytes": image_bytes},
        MinConfidence=90,  # 90% para Suggestive, 75% para violencia
    )
    labels = response.get("ModerationLabels", [])
    # Rechazar violencia/explícito con 75%+
    for label in labels:
        if label["Name"] in ("Violence", "Explicit Nudity") and label["Confidence"] >= 75:
            return False
        # Sugestivo rechazado solo con 90%+
        if label["Confidence"] >= 90:
            return False
    return True


def lambda_handler(event, context):
    body = json.loads(event.get("body", "{}"))
    prompt = body.get("prompt", "").strip()
    style = body.get("style", "realistic")
    user_id = body.get("user_id", "anonymous")

    # Validación de entrada
    if not prompt:
        return {"statusCode": 400, "body": json.dumps({"error": "El prompt no puede estar vacío"})}

    if not is_prompt_safe(prompt):
        return {"statusCode": 400, "body": json.dumps({"error": "El prompt contiene términos no permitidos"})}

    # Crear job asíncrono para evitar timeout de API Gateway (29s)
    job_id = str(uuid.uuid4())
    JOBS_TABLE.put_item(Item={
        "job_id": job_id,
        "user_id": user_id,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    # Construir payload para Stable Diffusion XL
    style_modifier = STYLE_MODIFIERS.get(style, STYLE_MODIFIERS["realistic"])
    full_prompt = f"{prompt}, {style_modifier}"

    payload = {
        "text_prompts": [
            {"text": full_prompt, "weight": 1.0},
            {"text": NEGATIVE_PROMPT, "weight": -1.0},
        ],
        "cfg_scale": 7,
        "steps": 50,
        "width": 1024,
        "height": 1024,
        "samples": 1,
    }

    try:
        resp = bedrock.invoke_model(
            modelId="stability.stable-diffusion-xl-v1",
            body=json.dumps(payload),
            contentType="application/json",
            accept="application/json",
        )

        result = json.loads(resp["body"].read())
        img_b64 = result["artifacts"][0]["base64"]
        img_bytes = base64.b64decode(img_b64)

        # Moderación de imagen generada
        if not is_image_safe(img_bytes):
            JOBS_TABLE.update_item(
                Key={"job_id": job_id},
                UpdateExpression="SET #s = :s, error = :e",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={":s": "rejected", ":e": "Imagen rechazada por moderación"},
            )
            return {"statusCode": 400, "body": json.dumps({"error": "Imagen rechazada por contenido inapropiado"})}

        # Guardar en S3 con cifrado AES-256
        key = f"images/{user_id}/{job_id}.png"
        s3.put_object(
            Bucket=BUCKET,
            Key=key,
            Body=img_bytes,
            ContentType="image/png",
            ServerSideEncryption="AES256",
            Metadata={
                "ai_generated": "true",
                "model": "stable-diffusion-xl-v1",
                "user_id": user_id,
                "prompt": prompt[:500],  # Truncar para metadata
                "style": style,
            },
        )

        # URL prefirmada válida por 1 hora
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET, "Key": key},
            ExpiresIn=3600,
        )

        # Actualizar estado del job
        JOBS_TABLE.update_item(
            Key={"job_id": job_id},
            UpdateExpression="SET #s = :s, image_url = :u, s3_key = :k, completed_at = :t",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":s": "completed",
                ":u": url,
                ":k": key,
                ":t": datetime.now(timezone.utc).isoformat(),
            },
        )

        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"job_id": job_id, "url": url, "key": key}),
        }

    except Exception as e:
        JOBS_TABLE.update_item(
            Key={"job_id": job_id},
            UpdateExpression="SET #s = :s, error = :e",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": "failed", ":e": str(e)},
        )
        return {"statusCode": 500, "body": json.dumps({"error": "Error generando imagen", "detail": str(e)})}
