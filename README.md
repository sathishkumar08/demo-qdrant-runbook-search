# Qdrant Runbook Search Demo

A small DevOps runbook search demo built with Streamlit, Qdrant, and local MiniLM embeddings.

Describe an issue, such as “My application cannot connect to the database,” and find matching troubleshooting guides based on meaning.

This is a local learning demo. The six sample runbooks are illustrative examples, not production incident procedures.

## How it works

1. The application converts each runbook’s title and content into an embedding.
2. Qdrant stores the embedding alongside the runbook text and metadata.
3. When you search, the application embeds your question using the same model.
4. Qdrant calculates similarity scores and returns matching runbooks.
5. Streamlit displays the results.

The embedding model is `sentence-transformers/all-MiniLM-L6-v2`, running locally through FastEmbed. Each embedding contains 384 numbers.

No generative LLM or paid embedding API is required.

## Requirements

- Python 3.12
- Docker Desktop, or Docker Engine with the Compose plugin
- Git
- OpenSSL
- Internet access for installing dependencies, pulling the Docker image, and downloading the embedding model

The commands below are for macOS and Linux.

## 1. Clone the repository

```bash
git clone https://github.com/sathishkumar08/demo-qdrant-runbook-search.git
cd demo-qdrant-runbook-search
```

## 2. Prepare Python

Create and activate a virtual environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Install the dependencies:

```bash
python -m pip install -r requirements.txt
python -m pip check
```

## 3. Create your API key

Run this once from the project folder:

```bash
printf 'QDRANT_API_KEY=%s\n' "$(openssl rand -hex 32)" > .env
chmod 600 .env
```

This creates a `.env` file containing a randomly generated API key. Running the command again replaces the existing key.

The `.env` file is excluded from Git. Do not commit it or include its contents in screenshots.

Docker Compose reads this file to configure Qdrant’s API-key authentication. The Python application must use the same key.

The application defaults to `http://127.0.0.1:6333`. You can override this by setting `QDRANT_URL`.

## 4. Start Qdrant

Make sure Docker is running, then execute:

```bash
docker compose up -d
docker compose ps
```

Qdrant uses the pinned image `qdrant/qdrant:v1.20.0`. Its REST API is published only on the local loopback address, and database files are stored in a named Docker volume.

To inspect startup logs:

```bash
docker compose logs --tail=50 qdrant
```

Open the dashboard:

http://127.0.0.1:6333/dashboard

When prompted, enter the API key from your local `.env` file.

## 5. Start the application

With your virtual environment active, load the environment variables into your terminal session:

```bash
set -a
source .env
set +a
```

Start Streamlit:

```bash
python -m streamlit run app.py --server.address 127.0.0.1
```

Open:

http://127.0.0.1:8501

Python does not automatically read `.env`. Repeat the environment-loading commands whenever you start the application from a new terminal session.

## 6. Load the sample runbooks

Click **Load sample runbooks** in the sidebar.

The first load downloads the embedding model and may take a few minutes. Later loads reuse the cached model.

The application loads six runbooks covering:

- Production PostgreSQL connectivity
- Staging PostgreSQL connectivity
- Kubernetes pod restarts
- Staging container memory issues
- TLS certificate renewal
- Staging DNS troubleshooting

The samples are defined in `RUNBOOKS` inside `app.py`.

Each runbook becomes a point in the `devops_runbooks_minilm_v1` collection, containing:

- **ID:** A stable identifier for the runbook
- **Vector:** The 384-dimensional embedding used for similarity search
- **Payload:** The title, content, service, environment, and embedding-model name

Loading the samples again updates the same six IDs rather than creating duplicates. It does not delete other points already in the collection.

## 7. Try a search

Example questions:

- My application cannot connect to the database
- The container keeps restarting after running out of memory
- Users see an expired certificate warning
- The staging hostname does not resolve

Start with **Environment** set to **All**.

Then select **production** or **staging** and search again. Qdrant applies the environment filter when retrieving matches.

The **Maximum results** setting controls the maximum number of matches displayed. Fewer results may appear because of the environment filter or similarity threshold.

## Understanding similarity scores

The application uses cosine similarity and a minimum score of `0.30`, configured in `app.py`:

```python
MIN_SCORE = 0.30
```

Qdrant excludes matches below this threshold.

A similarity score is not a confidence percentage or a guarantee that a runbook will solve the issue. The threshold is a starting point for this demo and should be evaluated against representative questions.

Short queries such as “connection” may return no results. Try adding context, such as “The application times out when connecting to PostgreSQL.”

The threshold also does not reliably identify unrelated questions. An unrelated query may still return a match.

## Inspect the stored data

Open the Qdrant dashboard and select:

```text
devops_runbooks_minilm_v1
```

Inspect a point to view its vector and payload.

The application’s **View payload** section displays the text and metadata. The vector is stored separately in Qdrant.

Search questions are converted into vectors for querying; the application does not store them as new points.

## Check persistence

After loading the samples, restart Qdrant:

```bash
docker compose restart qdrant
```

Wait for it to become ready, then search again without reloading the samples.

The stored points should remain because the database uses a named Docker volume.

## Stop the demo

Stop Streamlit with **Ctrl+C**, then run:

```bash
docker compose down
```

This preserves the database volume.

To permanently delete this demo’s stored database as well:

```bash
docker compose down -v
```

## Troubleshooting

### QDRANT_API_KEY is missing

Load the variables before starting Streamlit:

```bash
set -a
source .env
set +a
```

The key must be a generated value, not the example placeholder.

### Authentication fails

Confirm that the application and Qdrant use the same key.

If you changed `.env`, recreate the Qdrant container so it receives the updated configuration:

```bash
docker compose up -d --force-recreate qdrant
```

Stop Streamlit, reload `.env` into your terminal session, and start Streamlit again.

### Cannot connect to Qdrant

Check the container and its logs:

```bash
docker compose ps
docker compose logs --tail=50 qdrant
```

Confirm that port `6333` is available and that Qdrant has finished starting.

### Model download fails

Check internet access and any proxy restrictions. The initial model download requires access to the model host.

### No results appear

Try a more descriptive question or select **All** environments.

Results must meet the minimum similarity score. Changing the threshold affects both useful and irrelevant matches.

### Port 8501 is already in use

Start Streamlit on another port:

```bash
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8502
```

Then open http://127.0.0.1:8502.

### Changing the embedding model

Use a new collection and regenerate the document embeddings when changing models, even if both models produce the same number of dimensions.

Embeddings from different models should not be mixed.

## Files

| File | Purpose |
|---|---|
| `app.py` | Streamlit interface, sample runbooks, embedding generation, and search |
| `compose.yaml` | Local Qdrant server with API-key authentication and persistent storage |
| `requirements.txt` | Python dependencies |
| `.gitignore` | Excludes local secrets and generated files |

## Demo scope

Both Qdrant and Streamlit bind to localhost. API-key authentication protects Qdrant; it does not add user login to Streamlit.

For a remote deployment, use HTTPS, appropriate network restrictions, and your deployment platform’s secret-management mechanism.

The sample runbooks are short. Longer documents need a chunking strategy that respects the embedding model’s input limit.

## Validation scope

Development checks covered embedding generation, indexing, repeated loading, and environment filtering using Qdrant’s local in-memory mode.

These checks do not establish that the Docker server’s authentication or persistence works end to end. Verify those paths locally before treating the setup as validated.

## References

- [Qdrant documentation](https://qdrant.tech/documentation/)
- [FastEmbed documentation](https://qdrant.tech/documentation/fastembed/)
- [Qdrant Python client](https://github.com/qdrant/qdrant-client)
- [MiniLM model](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
- [Streamlit documentation](https://docs.streamlit.io/)
