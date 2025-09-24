import os, json, boto3, time
table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])

def handler(event, context):
    body = {"ts": int(time.time())}
    table.put_item(Item={"pk": "test", "sk": str(body["ts"]), "msg": "hello ddb"})
    return {"statusCode": 200, "body": json.dumps({"ok": True, "wrote": body})}