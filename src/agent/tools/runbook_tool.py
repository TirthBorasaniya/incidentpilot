"""Tool for semantic search over the runbook corpus in Qdrant."""

import os

from fastembed import TextEmbedding
from langchain_core.tools import tool
from qdrant_client import QdrantClient

from src.agent.tools.validation import (
    MAX_QUERY_CHARS,
    ToolInputError,
    validate_text,
)

EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"
TOP_K = 2


@tool
def search_runbooks(query: str) -> str:
    """
    Search the runbook corpus for sections relevant to the query.

    Parameters
    ----------
    query : str
        Natural language description of the failure or symptom.

    Returns
    -------
    result : str
        Top-2 matching runbook sections concatenated with separators.
    """
    qdrant_url = os.environ["QDRANT_URL"]
    collection_name = os.environ["QDRANT_COLLECTION"]

    try:
        query = validate_text(query, MAX_QUERY_CHARS, "query")
    except ToolInputError as error:
        return f"Rejected search_runbooks call: {error}"

    try:
        embedding_model = TextEmbedding(EMBEDDING_MODEL_NAME, threads=1)
        query_vector = list(embedding_model.embed([query]))[0].tolist()

        client = QdrantClient(url=qdrant_url)
        search_results = client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=TOP_K,
        )

        sections_list = [
            f"### {point.payload['title']}\n{point.payload['content']}\n\n---\n"
            for point in search_results
        ]
        return "".join(sections_list)
    # the broad catch is deliberate: the Qdrant client and fastembed raise a
    # wide range of unrelated error types, and a tool that raises would break
    # the agent loop instead of letting it degrade and report the failure
    except Exception as error:  # noqa: BLE001
        print(f"search_runbooks failed: {error}")
        return f"Failed to search runbook corpus: {error}"
