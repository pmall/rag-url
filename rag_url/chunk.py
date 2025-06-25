import os
import time
import json
import frontmatter
from pathlib import Path
from google import genai
from google.genai import types
from pydantic import BaseModel
from rag_url.prompts import CHUNKING_SYSTEM_PROMP, CHUNKING_PROMPT_TEMPLATE


class Chunk(BaseModel):
    title: str
    content: str
    keywords: list[str]


class MarkdownChunker:
    def __init__(self, workdir: str, delay: float = 1.0):
        self.workpath = Path(workdir)
        self.delay = delay

    def _to_chunks(self, content: str) -> list[Chunk]:
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash")

        if not GEMINI_API_KEY:
            raise Exception("GEMINI_API_KEY env var must be defined")

        client = genai.Client()

        response = client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=CHUNKING_PROMPT_TEMPLATE(content),
            config=types.GenerateContentConfig(
                system_instruction=CHUNKING_SYSTEM_PROMP,
                response_mime_type="application/json",
                response_schema=list[Chunk],
            ),
        )

        return json.loads(response.text or "[]")

    def chunk_file(self, infile: str) -> None:
        # do nothing if target file exists.
        outfilepath = self.workpath / f"{Path(infile).stem}.json"

        if outfilepath.exists():
            return

        # parse the source file.
        parsed = frontmatter.load(infile)

        url = parsed.metadata.get("url")
        content = parsed.content

        # ensure theres an url metadata.
        if not url:
            raise Exception(f"File {infile} has no url metadata")

        # run the llm to get chunks.
        chunks = self._to_chunks(content)

        # write to the outfile.
        wrapped = {"url": str(url), "chunks": chunks}

        with open(outfilepath, "w", encoding="utf-8") as f:
            f.write(json.dumps(wrapped, indent=2))

        print(f"[INFO] {infile} chunked in {outfilepath}")

    def run(self) -> tuple[int, int]:
        # loop over all souce file and produce chunk files.
        source_files = list(self.workpath.glob("*.md"))

        for infilepath in source_files:
            try:
                self.chunk_file(str(infilepath))

            except Exception as e:
                print(f"[ERROR] unable to chunk {infilepath}: {e}")

            time.sleep(self.delay)

        # count the produced files (some LLM calls may have failed).
        target_files = list(self.workpath.glob("*.json"))

        # return number of source files vs number of target file produced.
        # Orchetstrator might loop until completed.
        return (len(source_files), len(target_files))
