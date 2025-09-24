import os, json, base64, boto3

textract = boto3.client(
    "textract",
    region_name=os.environ.get("TEXTRACT_REGION", "us-east-2")
)
DOC_BUCKET = os.environ.get("DOC_BUCKET", "")

def _ok(obj):  return {"statusCode": 200, "headers":{"content-type":"application/json"}, "body": json.dumps(obj)}
def _err(e):   return {"statusCode": 500, "body": str(e)}

def _lines_from_blocks(blocks):
    return [b["Text"] for b in blocks if b.get("BlockType") == "LINE"]

def handler(event, context):
    route = event.get("routeKey")       # 'POST /process-doc' or 'GET /process-doc/{jobId}'
    try:
        if route == "POST /process-doc":
            return _post_process(event)
        elif route == "GET /process-doc/{jobId}":
            job_id = (event.get("pathParameters") or {}).get("jobId")
            return _get_status(job_id)
        else:
            return {"statusCode": 404, "body": "Unknown route"}
    except Exception as e:
        return _err(e)

def _post_process(event):
    body = json.loads(event.get("body") or "{}")

    # ---- Option 1: Sync via base64 (images; good for quick tests; size <= ~10MB API limit)
    if "imageBase64" in body:
        data = base64.b64decode(body["imageBase64"])
        # Choose operation: DetectDocumentText (text lines) or AnalyzeDocument (forms/tables)
        mode = body.get("mode", "detect")  # 'detect' | 'analyze'
        if mode == "analyze":
            features = body.get("features", ["FORMS", "TABLES"])
            resp = textract.analyze_document(Document={"Bytes": data}, FeatureTypes=features)
            return _ok({"features": features, "summary": f"Blocks: {len(resp.get('Blocks', []))}"})
        else:
            resp = textract.detect_document_text(Document={"Bytes": data})
            lines = _lines_from_blocks(resp.get("Blocks", []))
            return _ok({"lines": lines, "count": len(lines)})

    # ---- Option 2: S3 object
    bucket = body.get("bucket") or DOC_BUCKET
    key = body.get("key")
    if bucket and key:
        mode = body.get("mode", "async")  # 'async' -> multi-page PDFs; 'detect' -> sync on images in S3
        if mode == "detect":
            # detect_document_text supports images (PNG/JPG). Prefer async for PDFs/long docs.
            resp = textract.detect_document_text(Document={"S3Object": {"Bucket": bucket, "Name": key}})
            lines = _lines_from_blocks(resp.get("Blocks", []))
            return _ok({"lines": lines, "count": len(lines), "bucket": bucket, "key": key})
        elif mode == "analyze":
            features = body.get("features", ["FORMS", "TABLES"])
            resp = textract.analyze_document(Document={"S3Object": {"Bucket": bucket, "Name": key}},
                                             FeatureTypes=features)
            return _ok({"features": features, "summary": f"Blocks: {len(resp.get('Blocks', []))}"})
        else:
            # async job for PDFs / multi-page
            # choose StartDocumentTextDetection or StartDocumentAnalysis
            job_type = body.get("jobType", "text")  # 'text' | 'analysis'
            if job_type == "analysis":
                r = textract.start_document_analysis(
                    DocumentLocation={"S3Object": {"Bucket": bucket, "Name": key}},
                    FeatureTypes=body.get("features", ["FORMS", "TABLES"])
                )
            else:
                r = textract.start_document_text_detection(
                    DocumentLocation={"S3Object": {"Bucket": bucket, "Name": key}}
                )
            return _ok({"jobId": r["JobId"], "bucket": bucket, "key": key, "jobType": job_type})

    return {"statusCode": 400, "body": "Provide imageBase64 or {bucket,key}."}

def _get_status(job_id: str):
    if not job_id:
        return {"statusCode": 400, "body": "missing jobId"}
    # Try both "text" and "analysis" getters; whichever succeeds first.
    try:
        r = textract.get_document_text_detection(JobId=job_id)
        status = r["JobStatus"]
        if status != "SUCCEEDED":
            return _ok({"jobId": job_id, "status": status})
        lines = []
        while True:
            lines.extend(_lines_from_blocks(r.get("Blocks", [])))
            if "NextToken" in r:
                r = textract.get_document_text_detection(JobId=job_id, NextToken=r["NextToken"])
            else:
                break
        return _ok({"jobId": job_id, "status": "SUCCEEDED", "count": len(lines), "lines": lines})
    except textract.exceptions.InvalidJobIdException:
        return {"statusCode": 404, "body": "job not found"}
    except Exception:
        # Maybe it's an analysis job—try that:
        r = textract.get_document_analysis(JobId=job_id)
        status = r["JobStatus"]
        if status != "SUCCEEDED":
            return _ok({"jobId": job_id, "status": status})
        blocks = r.get("Blocks", [])
        return _ok({"jobId": job_id, "status": "SUCCEEDED", "blocks": len(blocks)})
