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
    resp = table.scan(Limit=25)
    items = to_native(resp.get("Items", []))
    return {
        "statusCode": 200,
        "headers": {"content-type": "application/json"},
        "body": json.dumps({"items": items})
    }