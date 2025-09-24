import os, json, boto3
table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])

def handler(event, context):
    pid = (event.get("pathParameters") or {}).get("id")
    if not pid: return {"statusCode": 400, "body": "missing id"}

    try:
        data = json.loads(event.get("body") or "{}")
    except Exception:
        return {"statusCode": 400, "body": "invalid json"}

    expr, names, vals = "SET #n=:n", {"#n":"name"}, {":n": data.get("name","updated")}
    table.update_item(
        Key={"pk":"ITEM","sk":pid},
        UpdateExpression=expr,
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=vals
    )
    return {"statusCode": 204, "body": ""}  # No Content
