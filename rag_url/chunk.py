import os
import time
import json
import re
import frontmatter
from pathlib import Path
from typing import TypedDict, Optional
from google import genai
from google.genai import types
from rag_url.prompts import CHUNKING_SYSTEM_PROMP, CHUNKING_PROMPT_TEMPLATE


class Chunk(TypedDict):
    title: str
    content: str
    code: Optional[str]


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
        # Clean up the response
        first_hash = markdown.find("#")
        if first_hash != -1:
            markdown = markdown[first_hash:]
        end_marker = markdown.find(self.stop_sequence)
        if end_marker != -1:
            markdown = markdown[:end_marker]

        # Split into chunks
        chunks = markdown.split(self.chunk_separator)
        results = []

        for i, chunk_str in enumerate(chunks):
            chunk_str = chunk_str.strip()
            if not chunk_str:
                continue

            lines = chunk_str.split('\n')
            
            # Stricter title parsing
            title_line = lines[0].strip()
            if not title_line.startswith('#') or title_line.startswith('```'):
                print(f"[ERROR] Chunk {i+1} has a malformed title. Skipping.")
                continue

            title = title_line.lstrip('#').strip()
            
            content_lines = lines[1:]
            content = '\n'.join(content_lines).strip()
            
            # Extract code block
            code_block_match = re.search(r"\n```(.*?)```$", content, re.DOTALL)
            code = None
            if code_block_match:
                code = code_block_match.group(1).strip()
                # Remove the code block from the content
                content = content[:code_block_match.start()].strip()

            if title and content:
                results.append(Chunk(title=title, content=content, code=code))

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
