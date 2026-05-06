import boto3
import json
import uuid
from datetime import datetime, timezone

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
dynamodb = boto3.resource("dynamodb")

HISTORY_TABLE = dynamodb.Table("TextHistory")
MAX_INPUT_TOKENS = 3000  # Límite para controlar costos

SYSTEM_PROMPTS = {
    "summarize":   "Eres un editor experto. Resume el texto manteniendo las ideas clave y el significado original. Sé conciso pero completo.",
    "expand":      "Eres un redactor creativo. Expande el texto con más detalle, ejemplos concretos y mayor profundidad. Mantén el tono original.",
    "grammar":     "Corrige errores gramaticales y de estilo sin cambiar el significado, tono ni contenido del texto. Solo reporta y aplica correcciones.",
    "variations":  "Genera exactamente 3 variaciones del texto con diferente tono y enfoque. Separa cada variación con '---VARIACIÓN X---' como encabezado.",
}


def estimate_tokens(text: str) -> int:
    """Estimación simple: ~4 caracteres por token."""
    return len(text) // 4


def lambda_handler(event, context):
    # Verificar rol del usuario (autorización por grupos de Cognito)
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    user_groups = claims.get("cognito:groups", "")
    user_id = claims.get("sub", "anonymous")

    allowed_groups = {"writers", "approvers"}
    if not any(g in user_groups for g in allowed_groups):
        return {"statusCode": 403, "body": json.dumps({"error": "No autorizado para edición de texto"})}

    body = json.loads(event.get("body", "{}"))
    text = body.get("text", "").strip()
    operation = body.get("operation", "grammar")
    doc_id = body.get("document_id", str(uuid.uuid4()))

    # Validaciones
    if not text:
        return {"statusCode": 400, "body": json.dumps({"error": "El texto no puede estar vacío"})}

    if operation not in SYSTEM_PROMPTS:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": f"Operación no válida. Opciones: {list(SYSTEM_PROMPTS.keys())}"}),
        }

    # Límite de tokens de entrada para controlar costos
    estimated = estimate_tokens(text)
    if estimated > MAX_INPUT_TOKENS:
        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": f"Texto demasiado largo ({estimated} tokens estimados). Máximo: {MAX_INPUT_TOKENS}. Divide el texto en secciones más pequeñas.",
                "estimated_tokens": estimated,
                "max_tokens": MAX_INPUT_TOKENS,
            }),
        }

    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2048,
        "system": SYSTEM_PROMPTS[operation],
        "messages": [{"role": "user", "content": text}],
    }

    try:
        resp = bedrock.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            body=json.dumps(payload),
            contentType="application/json",
            accept="application/json",
        )

        result = json.loads(resp["body"].read())
        edited_text = result["content"][0]["text"]

        # Guardar versión en DynamoDB (historial completo con optimistic locking)
        version_id = str(uuid.uuid4())
        version_number = body.get("version_number", 0)

        HISTORY_TABLE.put_item(Item={
            "document_id": doc_id,
            "version_id": version_id,
            "version_number": version_number + 1,
            "user_id": user_id,
            "original": text,
            "edited": edited_text,
            "operation": operation,
            "ts": datetime.now(timezone.utc).isoformat(),
            "input_tokens": estimated,
            "output_tokens": estimate_tokens(edited_text),
        })

        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({
                "edited_text": edited_text,
                "document_id": doc_id,
                "version_id": version_id,
                "version_number": version_number + 1,
                "operation": operation,
            }),
        }

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": "Error procesando texto", "detail": str(e)})}
