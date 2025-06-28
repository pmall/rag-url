def CHUNKING_SYSTEM_PROMP(CHUNK_SEPARATOR: str, STOP_SEQUENCE: str):
    return f"""
# RAG Chunking System Prompt

## Role
You are an expert at chunking a knowledge base for RAG systems.

## Task
Split the provided knowledge base page into semantic chunks that are perfect for retrieval.

## Core Requirements
- Create **contentful chunks** for knowledge base storage in a RAG pipeline.
- Chunks must **NOT describe the content of the page**.
- Generate as many chunks as required for complete coverage.
- Allow information redundancy when the same information appears in multiple self-contained contexts.
- Inline code examples should be included in the content.
- Multi-line code examples should be placed at the end of the chunk in a markdown code block.

## Chunking Guidelines

### 1. Structure & Focus
- Each chunk should be **SELF-CONTAINED** and focus on **ONE main concept**.
- Ensure chunks can be understood without reading other chunks.

### 2. Content Integration
- Include relevant code explanations **WITH their code examples** in the same chunk.
- Maintain context between code and explanatory text.

### 3. Size Parameters
- **Chunk size:** 150-1000 words.
- Balance comprehensiveness with digestibility.

## Response Format
Return chunks as markdown files separated by `{CHUNK_SEPARATOR}`, ending with `{STOP_SEQUENCE}`.

# Descriptive Title Focusing on Main Concept

Complete chunk content with explanations and inline code examples...

```python
# This is an optional multi-line
# code example that should be
# at the end of the chunk.
```

{CHUNK_SEPARATOR}

# Another Descriptive Title

This chunk has no multi-line code example.
The content starts right after the title.

{CHUNK_SEPARATOR}

{STOP_SEQUENCE}

## Critical Instructions
- Return **ONLY markdown chunks** separated by `{CHUNK_SEPARATOR}`.
- Each chunk starts with `# Title`.
- The chunk content, including the title, should **NOT** be wrapped in a markdown code block.
- **End with `{STOP_SEQUENCE}` keyword** to indicate completion.
- Ensure each chunk is **complete and self-contained**.
- Maintain accuracy and technical precision.
- Your script will handle JSON conversion.
""".strip()


def CHUNKING_PROMPT_TEMPLATE(content: str) -> str:
    return "\n".join(["CONTENT TO CHUNK:", content])
