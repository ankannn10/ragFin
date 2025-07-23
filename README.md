# ragFin

**ragFin** is an end-to-end Retrieval-Augmented Generation (RAG) platform for financial filings, featuring robust document ingestion, hybrid retrieval, and a modern conversational dashboard. It is designed for extracting, searching, and conversing over SEC 10-K filings and similar financial documents.

---

## Features

- **Conversational RAG**: Chat with your filings, ask follow-up questions, and get context-aware answers.
- **Hybrid Retrieval**: Combines dense (vector) and sparse (BM25/Elasticsearch) search for high-precision results.
- **Section & Subsection-Aware Chunking**: Splits filings into meaningful, LLM-friendly chunks with metadata.
- **Conversational Memory**: Remembers previous turns, rewrites follow-up queries, and summarizes long conversations.
- **Modern Dashboard**: Upload filings, view stats, and chat—all in a beautiful Next.js frontend.
- **Scalable & Modular**: Dockerized microservices, Celery workers, Redis, MinIO, Qdrant, and Elasticsearch.

---

## Project Structure

```
ragFin/
  backend/         # FastAPI, Celery, retrieval, embedding, and ingestion logic
    app/           # API entrypoint, config, dependencies
    services/      # Retrieval, generation, conversation, sparse indexer
    workers/       # Ingestion, sectioning, embedding
    utils/         # SSE utilities
    requirements.txt
    Dockerfile
  frontend/        # Next.js dashboard (React, TailwindCSS)
    app/           # Main pages and layout
    components/    # Chat, Upload, Sidebar, FilingsTable, MetricsCard, UI
    lib/           # Frontend utilities
    package.json
    Dockerfile
  docker-compose.yml
  ...
```

---

## Quickstart

### 1. **Clone the Repo**

```bash
git clone https://github.com/yourusername/ragFin.git
cd ragFin
```

### 2. **Build and Start All Services**

```bash
docker compose up --build
```

- Backend API: [http://localhost:8000/docs](http://localhost:8000/docs)
- Frontend: [http://localhost:3000](http://localhost:3000)
- MinIO Console: [http://localhost:9001](http://localhost:9001) (user/pass: `minioadmin`)
- Qdrant: [http://localhost:6333](http://localhost:6333)
- Elasticsearch: [http://localhost:9200](http://localhost:9200)

### 3. **Upload a Filing**

- Go to the dashboard ([http://localhost:3000](http://localhost:3000))
- Use the "Upload Filing" section to upload a PDF (e.g., 10-K)

### 4. **Chat with Your Data**

- Use the chat interface to ask questions about the uploaded filings.
- Example:  
  > "What was Apple's total revenue in 2023?"  
  > "And 2022?" (follow-up)

---

## How It Works

1. **Ingestion**: Upload a PDF. The backend splits it into sections/subsections, embeds chunks, and stores them in Qdrant/Elasticsearch.
2. **Retrieval**: User queries are embedded and matched against stored chunks using hybrid search.
3. **Conversational Memory**: The system rewrites follow-up queries using recent conversation turns and summaries.
4. **Answer Generation**: Retrieved context is sent to an LLM (e.g., Gemini) to generate a natural language answer.
5. **Frontend**: The Next.js dashboard provides upload, stats, and chat interfaces.

---

## Tech Stack

- **Backend**: FastAPI, Celery, Qdrant, Elasticsearch, Redis, MinIO, Sentence Transformers, Google Gemini
- **Frontend**: Next.js, React, TailwindCSS, TypeScript
- **Infrastructure**: Docker Compose

---

## Backend Dependencies

See `backend/requirements.txt` for full list. Key packages:
- `fastapi`, `uvicorn`, `celery`, `redis`, `boto3`, `qdrant-client`, `elasticsearch`, `sentence-transformers`, `torch`, `google-generativeai`, `tiktoken`

## Frontend Dependencies

See `frontend/package.json` for full list. Key packages:
- `next`, `react`, `tailwindcss`, `framer-motion`, `react-dropzone`, `clsx`

---

## Configuration

- **Environment Variables**: See `backend/app/config.py` for all configurable settings (S3, Redis, Qdrant, Elasticsearch, Gemini API key, etc.)
- **.env File**: Place your secrets and overrides in a `.env` file at the project root.

---

## Example API Usage

- **Upload a file**:
  ```bash
  curl -F "file=@apple-10k-2023.pdf" http://localhost:8000/upload
  ```
- **Ask a question**:
  ```bash
  curl -X POST "http://localhost:8000/rag/query/" \
    -H "Content-Type: application/json" \
    -d '{"query": "What was Apple total revenue in 2023?"}'
  ```

---

## Advanced Features

- **Conversational Summary Buffer Memory**: See `CONVERSATIONAL_SUMMARY_BUFFER_MEMORY.md` for details on how the system manages long conversations and context.
- **Hybrid Retrieval**: Combines dense and sparse search for best results.
- **Section/Subsection Metadata**: Chunks are tagged with item numbers and subsection titles for precise retrieval.

---

## Data & Tables

- **Tables**: Table extraction is not used in the current RAG pipeline. All answers are generated from text chunks.
- **CSV Exports**: Any CSVs in `/tables` or `/extracted_tables` are for manual analysis only.

---

## Development & Testing

- **Backend**:  
  ```bash
  cd backend
  uvicorn app.main:app --reload
  ```
- **Frontend**:  
  ```bash
  cd frontend
  npm install
  npm run dev
  ```
- **Celery Worker**:  
  ```bash
  cd backend
  celery -A celery_app.celery_app worker --loglevel=info
  ```

---

## Useful Commands

- View logs:  
  `docker compose logs -f frontend`  
  `docker compose logs -f api`
- Rebuild everything:  
  `docker compose up --build`
- Access MinIO:  
  [http://localhost:9001](http://localhost:9001) (user/pass: `minioadmin`)

---


## Contributing

Pull requests and issues are welcome! Please open an issue to discuss your ideas or report bugs.

---

## License

This project is licensed under the Apache 2.0 License.

---

**ragFin** — Conversational RAG for Financial Filings.
