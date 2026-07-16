import os
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

from config import (
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL_NAME,
    INDEX_CHUNK_OVERLAP,
    INDEX_CHUNK_SIZE,
    QDRANT_API_KEY_ENV,
    QDRANT_COLLECTION_NAME,
    QDRANT_URL_ENV,
    SAMPLE_CODEBASE_DIRECTORY,
    SUPPORTED_EXTENSIONS,
)

client = QdrantClient(
    url=os.getenv(QDRANT_URL_ENV),
    api_key=os.getenv(QDRANT_API_KEY_ENV),
)
embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)


def create_collection():
    try:
        client.delete_collection(QDRANT_COLLECTION_NAME)
    except Exception:
        pass

    client.create_collection(
        collection_name=QDRANT_COLLECTION_NAME,
        vectors_config=VectorParams(
            size=EMBEDDING_DIMENSIONS,
            distance=Distance.COSINE,
        ),
    )


def chunk_file(filepath, chunk_size=INDEX_CHUNK_SIZE):
    if chunk_size <= INDEX_CHUNK_OVERLAP:
        raise ValueError("chunk_size must be greater than INDEX_CHUNK_OVERLAP")

    with open(filepath, "r", errors="ignore") as file_handle:
        lines = file_handle.readlines()

    chunks = []
    step = chunk_size - INDEX_CHUNK_OVERLAP
    for index in range(0, len(lines), step):
        chunk = "".join(lines[index:index + chunk_size])
        if chunk.strip():
            chunks.append(
                {
                    "text": chunk,
                    "file": os.path.basename(filepath),
                    "start_line": index + 1,
                }
            )
    return chunks


def index_directory(directory):
    create_collection()
    points = []

    for root, _, files in os.walk(directory):
        for file in files:
            if os.path.splitext(file)[1].lower() in SUPPORTED_EXTENSIONS:
                path = os.path.join(root, file)
                chunks = chunk_file(path)
                print(f" {file} → {len(chunks)} chunks")

                for chunk in chunks:
                    vector = embedder.encode(chunk["text"]).tolist()
                    points.append(
                        PointStruct(
                            id=str(uuid.uuid4()),
                            vector=vector,
                            payload=chunk,
                        )
                    )

    client.upsert(
        collection_name=QDRANT_COLLECTION_NAME,
        points=points,
    )
    print(f"\nDone. Indexed {len(points)} total chunks into Qdrant.")


if __name__ == "__main__":
    index_directory(SAMPLE_CODEBASE_DIRECTORY)
