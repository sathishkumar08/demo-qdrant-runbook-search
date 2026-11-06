# Qdrant — DevOps Runbook Search

A local Streamlit application with real MiniLM embeddings and Qdrant vector search. No LLM or paid embedding API is required. The six short runbooks are synthetic learning examples, not production incident procedures.

## Requirements

- Python 3.11 or 3.12
- Docker Desktop (running), or Docker Engine with the Compose plugin
- Internet access for dependency installation, the Docker image and the initial model download

Qdrant runs in Docker; Python runs on your laptop. Both interfaces bind to localhost. This is a local demo, not a production deployment.

## 1. Install

Extract the ZIP and open a terminal inside `qdrant-runbook-demo`.

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 2. Start Qdrant

```bash
docker compose up -d
docker compose ps
docker compose logs --tail=30 qdrant
```

Open http://localhost:6333/dashboard . If the server is still starting, wait until its logs report readiness and refresh.

The image is pinned to v1.14.1 as an explicit API baseline, not a claim that this is the latest release. Python dependencies have bounded version ranges; after validating your setup, save exact versions with `python -m pip freeze > requirements-lock.txt` for repeatable blog runs.

## 3. Start the application

macOS/Linux (with the virtual environment active):

```bash
python -m streamlit run app.py --server.address 127.0.0.1
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

Open http://localhost:8501 . Click **Load sample runbooks** in the sidebar. The first attempt downloads the embedding model and may take a few minutes. Later runs reuse the downloaded model cache.

You should see six points. Repeating the load updates the same IDs rather than creating duplicates. It does not delete unrelated points. Keep this dedicated demo collection separate from other data.

## 4. Try these searches

- `My application cannot connect to the database`
- `The container keeps restarting after running out of memory`
- `Users see an expired certificate warning`

Start with Environment = All. Then select production or staging and click Search again. All returned payloads must match the selected environment. Rankings are model-generated: inspect the actual results rather than promising a particular score. With no score threshold, even weak matches can appear, especially when requesting many results.

## 5. Inspect Qdrant

In the dashboard, open `devops_runbooks_minilm_v1` and inspect its points. Each has an integer ID, a 384-dimensional vector and a payload containing title, content, service, environment and embedding_model.

The app embeds title + content for ingestion, embeds the question using the same MiniLM model, and calls query_points with cosine similarity plus the optional payload filter. Qdrant retrieves documents; it does not generate an answer.

These short runbooks fit a small demo. Longer documents need token-aware chunking; MiniLM has a limited input length, so do not simply feed whole long manuals into this example. When changing embedding models, create a different collection and regenerate every document vector, even if the dimensions are unchanged.

## 6. Check persistence

```bash
docker compose restart qdrant
```

Wait for Qdrant to become ready, refresh the app and search without reloading the runbooks. The six points should remain because the named volume persists the database.

## Screenshot checklist for Medium

1. App after loading: model name and six stored points visible.
2. Qdrant dashboard: collection, 384 dimensions and an expanded point payload.
3. Database question with Environment = All and actual similarity scores.
4. The same question filtered to production; explain why staging disappears.
5. Optional: a second question about certificate expiry to show a different result.

## Stop

Stop Streamlit with Ctrl+C. Then:

```bash
docker compose down
```

This preserves the database volume. Only if you want to permanently delete this demo's database, use `docker compose down -v`.

## Troubleshooting

- Cannot connect: run `docker compose ps` and inspect Qdrant logs. Check port 6333 is free.
- Model download fails: check outbound access to the model host and your proxy settings. No Hugging Face token is normally needed for this public model.
- Port 8501 occupied: add `--server.port 8502` and open that port.
- Shape mismatch: use a fresh collection name for a different model; don't mix embeddings.
- No strong match: add a relevant short runbook. The highest-ranked result is not necessarily a useful answer.

## Files

- app.py: complete interface, ingestion and search code
- runbooks.json: editable sample data
- compose.yaml: local Qdrant with persistent storage
- requirements.txt: Python dependencies

## References

https://qdrant.tech/documentation/embeddings/fastembed/
https://github.com/qdrant/qdrant-client
https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_resource

## Validation performed

Tested Python syntax, initial Streamlit rendering, real MiniLM model download and embedding generation, indexing, repeat loading without duplicates, vector queries and both environment filters using QdrantClient local in-memory mode. Database question ranked PostgreSQL first (about 0.573); certificate question ranked TLS Certificate Renewal first (about 0.653). These are observed demo results, not guaranteed relevance scores for other texts.

Validation environment: Python 3.12, Streamlit 1.66.1, qdrant-client 1.20.0, FastEmbed 0.9.1. Docker was unavailable, so the Compose/server path and server persistence check still need to be run on your laptop.
