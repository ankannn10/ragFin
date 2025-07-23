#backend/workers/ingestion.py

from pathlib import Path
import tempfile
import fitz  # PyMuPDF
import boto3
import json
from app.config import settings
from celery_app import celery_app
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

        # Enhanced text extraction with page information
        doc = fitz.open(str(local))
        page_data = []
        
        for page_num, page in enumerate(doc):
            text = page.get_text()
            page_data.append({
                "page_num": page_num + 1,
                "text": text,
                "bbox": [page.rect.x0, page.rect.y0, page.rect.x1, page.rect.y1]
            })
        
        # Combine all text for backward compatibility
        text = "\n".join(page["text"] for page in page_data)

        # Save raw text blob to MinIO (backward compatible)
        txt_key = f"{object_key.rsplit('.',1)[0]}.txt"
        s3.upload_fileobj(BytesIO(text.encode()), "processed-filings", txt_key)
        
        # Save page-structured data for enhanced processing
        pages_key = f"{object_key.rsplit('.',1)[0]}.pages.json"
        s3.upload_fileobj(BytesIO(json.dumps(page_data).encode()), "processed-filings", pages_key)

        # Enqueue sectioning task
        signature(
            "workers.sectioning.split_sections",
            kwargs={"txt_key": txt_key, "pages_key": pages_key, "filename": filename},
        ).apply_async()



        print(f"[INGEST] Stored raw text {txt_key} and page data {pages_key} | {len(text)} chars across {len(page_data)} pages")