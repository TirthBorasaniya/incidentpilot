"""Index the runbook corpus into Qdrant for vector search."""

import os
import uuid

from dotenv import load_dotenv
from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

# ============= Constants =============

EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"
VECTOR_SIZE = 384
CHUNK_SIZE_CHARS = 500
CHUNK_OVERLAP_CHARS = 50
RUNBOOKS_DIR = "runbooks"

# fixed namespace so point IDs are stable across runs and processes; builtin
# hash() is seeded per process, so it would insert duplicates on every re-index
POINT_ID_NAMESPACE = uuid.UUID("6f9619ff-8b86-d011-b42d-00c04fc964ff")


def _build_point_id(filename: str, chunk_index: int) -> str:
    """
    Derive a deterministic Qdrant point ID for one runbook chunk.

    Parameters
    ----------
    filename : str
        Runbook file the chunk came from.
    chunk_index : int
        Zero-based position of the chunk within that file.

    Returns
    -------
    point_id : str
        UUID5 string, identical for the same chunk on every run, so
        re-indexing overwrites in place instead of duplicating.
    """
    return str(uuid.uuid5(POINT_ID_NAMESPACE, f"{filename}_{chunk_index}"))


def _extract_title(content: str) -> str:
    """One-line helper extracting the first H1 line from runbook content."""
    title_lines = [line for line in content.splitlines() if line.startswith("# ")]
    return title_lines[0].lstrip("# ").strip() if title_lines else "Untitled"


def _chunk_content(content: str) -> list[str]:
    """
    Split runbook content into overlapping fixed-size chunks.

    Parameters
    ----------
    content : str
        Full text content of a runbook file.

    Returns
    -------
    chunks_list : list[str]
        Text chunks of at most CHUNK_SIZE_CHARS characters, overlapping by
        CHUNK_OVERLAP_CHARS characters.
    """
    stride = CHUNK_SIZE_CHARS - CHUNK_OVERLAP_CHARS
    chunks_list = [
        content[start : start + CHUNK_SIZE_CHARS]
        for start in range(0, len(content), stride)
        if content[start : start + CHUNK_SIZE_CHARS].strip()
    ]
    return chunks_list


def ensure_collection(client: QdrantClient, collection_name: str) -> None:
    """
    Create the runbook collection in Qdrant if it does not already exist.

    Parameters
    ----------
    client : QdrantClient
        Connected Qdrant client instance.
    collection_name : str
        Name of the collection to create.
    """
    existing_collections = [
        collection.name for collection in client.get_collections().collections
    ]

    if collection_name in existing_collections:
        return

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )


def index_runbooks(client: QdrantClient, collection_name: str) -> tuple[int, int]:
    """
    Embed and upsert every runbook chunk into the Qdrant collection.

    Parameters
    ----------
    client : QdrantClient
        Connected Qdrant client instance.
    collection_name : str
        Name of the collection to upsert points into.

    Returns
    -------
    point_count : int
        Total number of points upserted across all runbook files.
    file_count : int
        Total number of runbook files processed.
    """
    embedding_model = TextEmbedding(EMBEDDING_MODEL_NAME)
    point_count = 0

    runbook_filenames = sorted(
        filename for filename in os.listdir(RUNBOOKS_DIR) if filename.endswith(".md")
    )

    for filename in runbook_filenames:
        file_path = os.path.join(RUNBOOKS_DIR, filename)

        with open(file_path, "r") as runbook_file:
            content = runbook_file.read()

        title = _extract_title(content)
        chunks_list = _chunk_content(content)
        embeddings_list = list(embedding_model.embed(chunks_list))

        points_list = [
            PointStruct(
                id=_build_point_id(filename, chunk_index),
                vector=embeddings_list[chunk_index].tolist(),
                payload={"title": title, "content": chunk_text, "filename": filename},
            )
            for chunk_index, chunk_text in enumerate(chunks_list)
        ]

        client.upsert(collection_name=collection_name, points=points_list)
        point_count += len(points_list)
        print(f"indexed {filename}: {len(points_list)} chunks")

    return point_count, len(runbook_filenames)


# ============= Main =============

if __name__ == "__main__":
    load_dotenv()

    qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    qdrant_collection = os.environ.get("QDRANT_COLLECTION", "runbooks")

    client = QdrantClient(url=qdrant_url)
    ensure_collection(client, qdrant_collection)
    total_points, total_files = index_runbooks(client, qdrant_collection)

    print(f"Indexed {total_files} files, {total_points} chunks, into {qdrant_collection}.")
