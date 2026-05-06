import boto3
import json

dynamodb = boto3.resource("dynamodb")
JOBS_TABLE = dynamodb.Table("Jobs")


def lambda_handler(event, context):
    job_id = event.get("pathParameters", {}).get("job_id")

    if not job_id:
        return {"statusCode": 400, "body": json.dumps({"error": "job_id requerido"})}

    try:
        result = JOBS_TABLE.get_item(Key={"job_id": job_id})
        item = result.get("Item")

        if not item:
            return {"statusCode": 404, "body": json.dumps({"error": "Job no encontrado"})}

        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({
                "job_id": job_id,
                "status": item.get("status"),          # pending | completed | failed | rejected
                "image_url": item.get("image_url"),
                "s3_key": item.get("s3_key"),
                "error": item.get("error"),
                "created_at": item.get("created_at"),
                "completed_at": item.get("completed_at"),
            }),
        }

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
