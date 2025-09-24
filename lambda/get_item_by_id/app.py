import os, json, boto3
table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])

from decimal import Decimal

def to_native(obj):
    if isinstance(obj, list):
        return [to_native(x) for x in obj]
    if isinstance(obj, dict):
        return {k: to_native(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        # if it’s an integer like 1737056789 -> int, otherwise float
        return int(obj) if obj % 1 == 0 else float(obj)
    return obj

def handler(event, context):
    pid = (event.get("pathParameters") or {}).get("id")
    if not pid:
        return {"statusCode": 400, "body": "missing id"}
    resp = table.get_item(Key={"pk": "ITEM", "sk": pid})
    item = resp.get("Item")
    if not item:
        return {"statusCode": 404, "body": "not found"}
    return {
        "statusCode": 200,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(to_native(item))
    }