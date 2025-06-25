import os
import time
import json
import frontmatter
from pathlib import Path
from typing import TypedDict
from google import genai
from google.genai import types
from rag_url.prompts import CHUNKING_SYSTEM_PROMP, CHUNKING_PROMPT_TEMPLATE


class Chunk(TypedDict):
    title: str
    content: str


class MarkdownChunker:
    def __init__(self, workdir: str, delay: float = 1.0):
        self.workpath = Path(workdir)
        self.delay = delay
        self.stop_sequence = "<STOP_RAG_CHUNKS>"
        self.chunk_separator = "<SEPARATOR_RAG_CHUNK>"

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
                system_instruction=CHUNKING_SYSTEM_PROMP(
                    self.chunk_separator, self.stop_sequence
                ),
                stop_sequences=[self.stop_sequence],
            ),
        )

        if not response.text:
            raise Exception("No response produced")

        chunks = self._response_to_chunks(response.text)

        if not chunks:
            raise Exception("No chunk produced")

        return chunks

    def _response_to_chunks(self, markdown: str) -> list[Chunk]:
        # Remove everything before the first #
        first_hash = markdown.find("#")
        if first_hash != -1:
            markdown = markdown[first_hash:]

        # Remove END_CHUNKS and everything after it
        end_marker = markdown.find(self.stop_sequence)
        if end_marker != -1:
            markdown = markdown[:end_marker]

        # Split by {self.chunk_separator} separator
        chunks = markdown.split(self.chunk_separator)

        # collect the results.
        results = []

        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue

            # Extract title (first line starting with #)
            lines = chunk.split("\n")
            title_line = next(
                (line for line in lines if line.strip().startswith("#")), None
            )

            if not title_line:
                continue

            # Extract title (remove # and strip)
            title = title_line.strip().lstrip("#").strip()

            # Extract content (everything after the title line)
            title_index = lines.index(title_line)
            content_lines = lines[title_index + 1 :]

            # Remove empty lines at the beginning
            while content_lines and not content_lines[0].strip():
                content_lines.pop(0)

            content = "\n".join(content_lines).strip()

            if title and content:
                results.append(Chunk(title=title, content=content))

        return results

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
