from pathlib import Path
import tempfile
import fitz  # PyMuPDF
import boto3
from app.config import settings
from celery_app import celery_app
import json
from io import BytesIO
from celery import signature 


s3 = boto3.client(
    "s3",
    endpoint_url=settings.s3_endpoint,
    aws_access_key_id=settings.s3_access_key,
    aws_secret_access_key=settings.s3_secret_key,
)

@celery_app.task(name="workers.ingestion.parse_file", bind=True, max_retries=3)
def parse_file(self, object_key: str, filename: str):
    with tempfile.TemporaryDirectory() as tmpd:
        local = Path(tmpd) / filename
        s3.download_file(settings.s3_bucket_raw, object_key, str(local))

        # text extraction
        doc = fitz.open(str(local))
        text = "\n".join(page.get_text() for page in doc)

        # ⬇️  NEW – save raw text blob to MinIO
        txt_key = f"{object_key.rsplit('.',1)[0]}.txt"
        s3.upload_fileobj(BytesIO(text.encode()), "processed-filings", txt_key)

        # ⬇️  NEW – enqueue sectioning task
        signature(
            "workers.sectioning.split_sections",
            kwargs={"txt_key": txt_key, "filename": filename},
        ).apply_async()

        print(f"[INGEST] Stored raw text {txt_key} | {len(text)} chars")