"""
Celery task: split a raw 10-K/10-Q text blob into *true* SEC sections
(Item 1, Item 1A, Item 7, …) and upload a JSONLines artefact.

Output key:
    <uuid>_<filename>.sections.jsonl
JSONL schema (one line per section):
    {"section": "ITEM 1.", "text": "<full body text of that item>"}
"""

import re, json, tempfile, boto3
from pathlib import Path
from app.config import settings
from celery_app import celery_app
from celery import signature
# ──────────────────────────────────────────────────────────────
# 1.  Local replica of your proven splitter logic
# ──────────────────────────────────────────────────────────────
ITEM_RE = re.compile(r"(ITEM\s+\d+[A-Za-z]?\.)", re.IGNORECASE)

def split_into_sections(text: str) -> dict[str, str]:
    """
    Return {"ITEM 1.": "...", "ITEM 1A.": "...", ...}.
    If no headings found, fallback key is "FULL_TEXT".
    """
    matches = list(ITEM_RE.finditer(text))
    if not matches:
        return {"FULL_TEXT": text}

    sections: dict[str, str] = {}
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        title = m.group(1).strip().upper()
        body  = text[start:end].strip()
        sections[title] = body
    return sections

# ──────────────────────────────────────────────────────────────
# 2.  S3 / MinIO client
# ──────────────────────────────────────────────────────────────
s3 = boto3.client(
    "s3",
    endpoint_url=settings.s3_endpoint,
    aws_access_key_id=settings.s3_access_key,
    aws_secret_access_key=settings.s3_secret_key,
)

# ──────────────────────────────────────────────────────────────
# 3.  Celery task
# ──────────────────────────────────────────────────────────────
@celery_app.task(name="workers.sectioning.split_sections",
                 bind=True, max_retries=3)
def split_sections(self, txt_key: str, filename: str):
    """
    Parameters
    ----------
    txt_key   : key of raw .txt object in processed-filings bucket
    filename  : original filename (for logging only)
    """
    # 1) fetch raw text saved by ingestion
    obj = s3.get_object(Bucket="processed-filings", Key=txt_key)
    raw_text = obj["Body"].read().decode()

    # 2) split into logical SEC items
    sections = split_into_sections(raw_text)

    # 3) write JSONL to a temp file
    jsonl_key = txt_key.replace(".txt", ".sections.jsonl")
    with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
        for title, body in sections.items():
            tmp.write(json.dumps({"section": title, "text": body}) + "\n")
        tmp_path = tmp.name

    # 4) upload to MinIO
    s3.upload_file(tmp_path, "processed-filings", jsonl_key)
    print(f"[SECTION] {filename}: {len(sections)} sections  →  {jsonl_key}")
    signature(
    "workers.embedding.embed_sections",
    kwargs={"sections_key": jsonl_key, "filename": filename},
).apply_async()
