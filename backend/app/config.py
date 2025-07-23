#backend/app/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # FastAPI
    api_prefix: str = "/api"
    # Storage
    s3_endpoint: str = "http://minio:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_raw: str = "raw-filings"
    # Broker / Result backend
    redis_url: str = "redis://redis:6379/0"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "sec_chunks_bge_v1"

    # Elasticsearch (sparse)
    es_host: str = "http://elasticsearch:9200"
    es_index: str = "sec_sparse_index"

    # Hybrid retrieval weight (α for dense similarity)
    hybrid_alpha: float = 0.7

    gemini_api_key: str
    gemini_model: str = "models/gemini-1.5-pro-latest"


settings = Settings()  # singleton

