import os

import streamlit as st
from fastembed import TextEmbedding
from qdrant_client import QdrantClient, models


MODEL = "sentence-transformers/all-MiniLM-L6-v2"
COLLECTION = "devops_runbooks_minilm_v1"
DIMENSIONS = 384
MIN_SCORE = 0.30

RUNBOOKS = [
    {
        "id": 1,
        "title": "PostgreSQL Connection Troubleshooting",
        "content": (
            "Application cannot connect to the database or reports connection "
            "timeouts. Check PostgreSQL availability, hostname, port 5432, "
            "DNS resolution, firewall rules and credentials. Inspect connection "
            "pool usage and database connection limits."
        ),
        "service": "postgresql",
        "environment": "production",
    },
    {
        "id": 2,
        "title": "Staging Database Connection Checks",
        "content": (
            "Staging application cannot connect to PostgreSQL. Verify the "
            "staging database endpoint, credentials, DNS and network access. "
            "Check whether the database is stopped and confirm the application "
            "uses staging secrets."
        ),
        "service": "postgresql",
        "environment": "staging",
    },
    {
        "id": 3,
        "title": "Kubernetes Pod Restart Troubleshooting",
        "content": (
            "A container keeps restarting or shows CrashLoopBackOff. Inspect "
            "pod events and previous container logs. Check exit codes, "
            "OOMKilled events, memory limits and liveness probes."
        ),
        "service": "kubernetes",
        "environment": "production",
    },
    {
        "id": 4,
        "title": "Staging Container Memory Troubleshooting",
        "content": (
            "A staging pod is killed after using too much memory. Check "
            "OOMKilled events, memory metrics and configured resource limits. "
            "Investigate memory leaks and workload size before increasing "
            "memory allocation."
        ),
        "service": "kubernetes",
        "environment": "staging",
    },
    {
        "id": 5,
        "title": "TLS Certificate Renewal",
        "content": (
            "Users see an expired certificate warning when opening the website. "
            "Check certificate expiry, hostname coverage and the certificate "
            "chain. Renew through the certificate provider and verify the new "
            "certificate is served by the load balancer."
        ),
        "service": "web",
        "environment": "production",
    },
    {
        "id": 6,
        "title": "Staging DNS Troubleshooting",
        "content": (
            "A staging hostname does not resolve or points to the wrong IP "
            "address. Check DNS records with dig or nslookup, the configured "
            "resolver and recent record changes. Compare authoritative "
            "responses and cached answers."
        ),
        "service": "dns",
        "environment": "staging",
    },
]


@st.cache_resource
def embedding_model():
    """Load the model once and reuse it across Streamlit reruns."""
    return TextEmbedding(model_name=MODEL)


def database():
    """Read the API key from the environment and configure the client."""
    api_key = os.environ.get("QDRANT_API_KEY", "").strip()

    if not api_key or api_key == "replace-with-a-generated-key":
        raise ValueError(
            "QDRANT_API_KEY is missing or still contains the placeholder."
        )

    return QdrantClient(
        url=os.getenv("QDRANT_URL", "http://127.0.0.1:6333"),
        api_key=api_key,
        timeout=30,
    )


def load_runbooks(client, encoder):
    if not client.collection_exists(COLLECTION):
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=models.VectorParams(
                size=DIMENSIONS,
                distance=models.Distance.COSINE,
            ),
        )

    texts = [
        f"{runbook['title']}\n{runbook['content']}"
        for runbook in RUNBOOKS
    ]

    vectors = list(encoder.embed(texts))

    points = [
        models.PointStruct(
            id=runbook["id"],
            vector=vector.tolist(),
            payload={
                **{
                    key: value
                    for key, value in runbook.items()
                    if key != "id"
                },
                "embedding_model": MODEL,
            },
        )
        for runbook, vector in zip(RUNBOOKS, vectors)
    ]

    # Reusing IDs updates existing points instead of creating duplicates.
    client.upsert(
        collection_name=COLLECTION,
        points=points,
        wait=True,
    )

    return len(points)


def search(client, encoder, question, environment, limit):
    query_vector = next(iter(encoder.embed([question]))).tolist()

    query_filter = None

    if environment != "All":
        query_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="environment",
                    match=models.MatchValue(value=environment),
                )
            ]
        )

    response = client.query_points(
        collection_name=COLLECTION,
        query=query_vector,
        query_filter=query_filter,
        limit=limit,
        score_threshold=MIN_SCORE,
        with_payload=True,
        with_vectors=False,
    )

    return response.points


def render_app(client):
    st.title("DevOps Runbook Search")
    st.write("Describe the problem. Find a relevant troubleshooting guide.")
    st.caption("Local MiniLM embeddings · Qdrant vector search · Demo")

    with st.sidebar:
        st.header("Demo setup")
        st.caption("Embedding model")
        st.write(MODEL)
        st.caption("384 dimensions · Cosine similarity")
        st.caption(f"Minimum similarity: {MIN_SCORE:.2f}")

        load_clicked = st.button(
            "Load sample runbooks",
            type="primary",
        )

        st.caption(
            "First load downloads the model. "
            "Re-loading updates the same six points."
        )

    with st.expander("View the sample dataset"):
        st.json(RUNBOOKS)

    if load_clicked:
        try:
            with st.spinner("Generating embeddings and loading runbooks…"):
                count = load_runbooks(client, embedding_model())

            st.success(f"{count} runbooks loaded into {COLLECTION}.")
        except Exception:
            st.error(
                "Loading failed. Check Qdrant connectivity, API-key "
                "permissions, and internet access for the model download."
            )
            return

    if not client.collection_exists(COLLECTION):
        st.info("Click Load sample runbooks in the sidebar to begin.")
        return

    count = client.count(
        collection_name=COLLECTION,
        exact=True,
    ).count

    st.caption(f"Stored points: {count}")

    with st.form("search"):
        question = st.text_input(
            "What problem are you investigating?",
            value="My application cannot connect to the database",
        )

        environment = st.selectbox(
            "Environment",
            ["All", "production", "staging"],
        )

        limit = st.slider(
            "Maximum results",
            min_value=1,
            max_value=6,
            value=3,
        )

        submitted = st.form_submit_button(
            "Search",
            type="primary",
        )

    if not submitted:
        return

    if not question.strip():
        st.warning("Enter a question first.")
        return

    try:
        with st.spinner("Searching runbooks…"):
            hits = search(
                client=client,
                encoder=embedding_model(),
                question=question.strip(),
                environment=environment,
                limit=limit,
            )
    except Exception:
        st.error(
            "Search failed. Check Qdrant connectivity and model availability."
        )
        return

    if not hits:
        st.info(
            "No relevant runbook found for your question and selected "
            "environment. Try describing a DevOps issue or select All "
            "environments."
        )
        st.caption(
            f"No matches met the minimum similarity score of {MIN_SCORE:.2f}."
        )
        return

    for rank, hit in enumerate(hits, start=1):
        payload = hit.payload or {}

        with st.container(border=True):
            st.subheader(
                f"{rank}. {payload.get('title', 'Untitled')}"
            )

            st.caption(
                f"{payload.get('environment')} · "
                f"{payload.get('service')} · "
                f"Similarity: {hit.score:.3f}"
            )

            st.write(payload.get("content", ""))

            with st.expander("View payload"):
                st.json(payload)

    st.caption(
        f"Showing matches with similarity of at least {MIN_SCORE:.2f}. "
        "Similarity is not a confidence percentage."
    )


def main():
    st.set_page_config(
        page_title="DevOps Runbook Search",
        page_icon="🔎",
        layout="centered",
    )

    api_key = os.environ.get("QDRANT_API_KEY", "").strip()

    if not api_key or api_key == "replace-with-a-generated-key":
        st.error(
            "Set QDRANT_API_KEY by loading your .env file before "
            "starting Streamlit."
        )
        return

    client = None

    try:
        client = database()
        render_app(client)
    except Exception:
        st.error(
            "Cannot complete the request. Check that Qdrant is running "
            "and the application uses the same API key as the server."
        )
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    main()