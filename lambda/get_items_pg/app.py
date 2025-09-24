import os, json, boto3, pg8000

DB_SECRET_ARN = os.environ["DB_SECRET_ARN"]
PG_HOST = os.environ["PG_HOST"]
PG_DB   = os.environ["PG_DB"]
PG_PORT = int(os.environ.get("PG_PORT", "5432"))
PG_TABLE = os.environ.get("PG_TABLE", "items")

sm = boto3.client("secretsmanager")

def _pg():
    sec = sm.get_secret_value(SecretId=DB_SECRET_ARN)["SecretString"]
    creds = json.loads(sec)
    return pg8000.connect(
        host=PG_HOST, database=PG_DB,
        user=creds["username"], password=creds["password"], port=PG_PORT
    )

def handler(event, context):
    try:
        conn = _pg()
        cur = conn.cursor()
        # list the newest 25 rows
        cur.execute(f"CREATE TABLE IF NOT EXISTS {PG_TABLE} (id uuid PRIMARY KEY, name text, created_at bigint)")
        cur.execute(f"SELECT id, name, created_at FROM {PG_TABLE} ORDER BY created_at DESC LIMIT 25")
        rows = [{"id": str(r[0]), "name": r[1], "created_at": int(r[2])} for r in cur.fetchall()]
        cur.close(); conn.close()
        return {
            "statusCode": 200,
            "headers": {"content-type":"application/json"},
            "body": json.dumps({"items": rows})
        }
    except Exception as e:
        return {"statusCode": 500, "body": f"db error: {e}"}
