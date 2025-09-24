# import os, json, boto3, uuid, time
# table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])

# def handler(event, context):
#     body = event.get("body") or "{}"
#     try:
#         data = json.loads(body)
#     except Exception:
#         return {"statusCode": 400, "body": "invalid json"}

#     item_id = str(uuid.uuid4())
#     item = {
#         "pk": "ITEM",
#         "sk": item_id,
#         "name": data.get("name", "unnamed"),
#         "created_at": int(time.time())
#     }
#     table.put_item(Item=item)
#     return {"statusCode": 201, "headers": {"content-type":"application/json"}, "body": json.dumps({"id": item_id})}

import os, json, time, uuid, boto3, pg8000

DB_SECRET_ARN = os.environ["DB_SECRET_ARN"]
PG_HOST = os.environ["PG_HOST"]
PG_DB   = os.environ["PG_DB"]
PG_PORT = int(os.environ.get("PG_PORT", "5432"))

sm = boto3.client("secretsmanager")

def _pg_conn():
    sec = sm.get_secret_value(SecretId=DB_SECRET_ARN)["SecretString"]
    creds = json.loads(sec)
    return pg8000.connect(
        host=PG_HOST,
        database=PG_DB,
        user=creds["username"],
        password=creds["password"],
        port=PG_PORT,
    )

def handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
    except Exception:
        body = {}

    name = body.get("name", "from-lambda")
    item_id = str(uuid.uuid4())
    now = int(time.time())

    try:
        conn = _pg_conn()
        cur = conn.cursor()
        # simple schema bootstrap for dev:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS items (
              id uuid PRIMARY KEY,
              name text,
              created_at bigint
            )
        """)
        cur.execute("INSERT INTO items (id, name, created_at) VALUES (%s, %s, %s)",
                    (item_id, name, now))
        conn.commit()
        cur.close(); conn.close()
        return {
            "statusCode": 201,
            "headers": {"content-type": "application/json"},
            "body": json.dumps({"id": item_id, "name": name, "via": "postgres"})
        }
    except Exception as e:
        # check CloudWatch Logs for full trace if this happens
        return {"statusCode": 500, "body": f"db error: {e}"}
