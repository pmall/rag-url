import os
import json
import lancedb
from pathlib import Path
from google import genai


class ChunkEmbedder:
    def __init__(self, dbfile: str, pattern: str, collection: str = "collection"):
        self.db = lancedb.connect(dbfile)
        self.pattern = pattern
        self.collection = collection

    def _embed_content(self, title: str, content: str):
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        GEMINI_EMBED_MODEL_NAME = os.getenv(
            "GEMINI_EMBED_MODEL_NAME", "text-embedding-004"
        )

        if not GEMINI_API_KEY:
            raise Exception("GEMINI_API_KEY env var must be defined")

        markdown = "\n\n".join([f"#{title}", content])

        client = genai.Client(api_key=GEMINI_API_KEY)

        response = client.models.embed_content(
            model=GEMINI_EMBED_MODEL_NAME,
            contents=markdown,
        )

        if not response.embeddings:
            raise Exception("Unable to embed content")

        # Extract the embedding vector from the response
        # The response contains embeddings as a list, we take the first one
        embedding_vector = response.embeddings[0].values

        return {
            "title": title,
            "content": content,
            "text": markdown,
            "vector": embedding_vector,
        }

    def run(self) -> None:
        docs = []

        for filepath in Path().glob(self.pattern):
            if not filepath.is_file():
                continue

            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"[INFO] Error reading {filepath}: {e}")
                continue

            url = data.get("url")
            content = data.get("chunks")

            if not isinstance(url, str):
                print(f"[INFO] Skipping {filepath}: no valid 'url'")
                continue

            if not isinstance(content, list):
                print(f"[INFO] Skipping {filepath}: no valid 'content'")
                continue

            num_docs = 0

            for item in content:
                title = item.get("title")
                chunk_content = item.get("content")

                if not isinstance(title, str):
                    print(f"[INFO] Skipping chunk in {filepath}: no valid 'title'")
                    continue

                if not isinstance(chunk_content, str):
                    print(f"[INFO] Skipping chunk in {filepath}: no valid 'content'")
                    continue

                try:
                    num_docs = num_docs + 1
                    embedding_doc = self._embed_content(title, chunk_content)
                    embedding_doc["url"] = url
                    docs.append(embedding_doc)
                except Exception as e:
                    print(f"[ERROR] Error embedding content from {filepath}: {e}")
                    continue

            print(f"[INFO] Successfully emeded {num_docs} documents from {filepath}")

        if docs:
            # Create or replace table with the new documents
            try:
                self.db.create_table(self.collection, data=docs, mode="overwrite")
                print(
                    f"Successfully created database {filepath} with {len(docs)} chunks"
                )
            except Exception as e:
                print(f"[ERROR] Error creating table: {e}")
