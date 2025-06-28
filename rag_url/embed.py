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

    def _embed_content(self, title: str, content: str, code: str, url: str):
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        GEMINI_EMBED_MODEL_NAME = os.getenv(
            "GEMINI_EMBED_MODEL_NAME", "text-embedding-004"
        )

        if not GEMINI_API_KEY:
            raise Exception("GEMINI_API_KEY env var must be defined")

        text_to_embed = "\n\n".join([f"#{title}", content])

        client = genai.Client(api_key=GEMINI_API_KEY)

        response = client.models.embed_content(
            model=GEMINI_EMBED_MODEL_NAME,
            contents=text_to_embed,
        )

        if not response.embeddings:
            raise Exception("Unable to embed content")

        embedding_vector = response.embeddings[0].values

        return {
            "text": text_to_embed,
            "vector": embedding_vector,
            "code": code,
            "url": url,
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
            chunks = data.get("chunks")

            if not isinstance(url, str):
                print(f"[INFO] Skipping {filepath}: no valid 'url'")
                continue

            if not isinstance(chunks, list):
                print(f"[INFO] Skipping {filepath}: no valid 'chunks'")
                continue

            num_docs = 0

            for item in chunks:
                title = item.get("title")
                content = item.get("content")
                code = item.get("code")

                if not isinstance(title, str) or not isinstance(content, str):
                    print(f"[INFO] Skipping chunk in {filepath}: invalid title or content")
                    continue

                try:
                    num_docs += 1
                    embedding_doc = self._embed_content(title, content, code, url)
                    docs.append(embedding_doc)
                except Exception as e:
                    print(f"[ERROR] Error embedding content from {filepath}: {e}")
                    continue

            print(f"[INFO] Successfully embedded {num_docs} documents from {filepath}")

        if docs:
            try:
                self.db.create_table(self.collection, data=docs, mode="overwrite")
                print(
                    f"Successfully created database with {len(docs)} chunks in collection '{self.collection}'"
                )
            except Exception as e:
                print(f"[ERROR] Error creating table: {e}")
