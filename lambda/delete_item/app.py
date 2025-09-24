import os, boto3
table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])

def handler(event, context):
    pid = (event.get("pathParameters") or {}).get("id")
    if not pid: return {"statusCode": 400, "body": "missing id"}
    table.delete_item(Key={"pk":"ITEM","sk":pid})
    return {"statusCode": 204, "body": ""}
