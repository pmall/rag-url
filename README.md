# RAG-URL

This project implements a complete, command-line-driven pipeline for converting the content of a website into a searchable knowledge base, which can then be queried through an interactive agent. It employs a Retrieval-Augmented Generation (RAG) architecture, utilizing Google's Gemini models for content processing and conversational AI, and LanceDB for efficient vector storage and retrieval.

## System Architecture and Pipeline

The system operates through a sequential four-step pipeline, managed via a command-line interface. Each step is a modular component that processes the output of the previous one.

### 1. Scrape

The initial step involves crawling and ingesting content from a target website.

- **Process**: The `BaseUrlScraper` class uses the `requests` library to perform HTTP requests and `BeautifulSoup` to parse HTML content. It starts from a given base URL and recursively follows all same-domain links to discover and download pages. To avoid fetching irrelevant content, specific URL paths can be excluded.
- **Content Conversion**: For each downloaded page, the raw HTML is cleaned, and the `trafilatura` library is used to convert the primary content into Markdown format. This focuses on extracting the core text while discarding boilerplate like navigation menus and footers.
- **Output**: Each scraped page is saved as a separate `.md` file in a designated working directory. The original source URL is preserved in the file's YAML frontmatter for traceability.

### 2. Chunk

After scraping, the raw Markdown content is segmented into smaller, semantically coherent chunks suitable for vector embedding and retrieval.

- **Process**: The `MarkdownChunker` class sends the content of each Markdown file to a Gemini model. A carefully designed system prompt (`CHUNKING_SYSTEM_PROMP`) instructs the model to break the text into self-contained chunks, each focusing on a single topic. The model is guided to include titles, content, and associated code blocks within each chunk.
- **Output**: The resulting chunks are stored in `.json` files. Each JSON file corresponds to an original source page and contains a list of structured chunk objects, including `title`, `content`, and optional `code` fields.

### 3. Embed

This step converts the textual chunks into numerical vector representations, enabling semantic search.

- **Process**: The `ChunkEmbedder` class iterates through the JSON files produced in the previous step. For each chunk, it concatenates the title and content and uses the `text-embedding-004` model via the Gemini API to generate a vector embedding. 
- **Data Storage**: The generated vector, along with the original text, any associated code, and the source URL, is compiled into a document.
- **Output**: All documents are collected and used to create a [LanceDB](https://lancedb.github.io/lancedb/) table. This creates a persistent, efficient vector database, which is overwritten on each run to ensure freshness.

### 4. Agent

The final component is an interactive command-line agent that allows users to query the knowledge base.

- **Process**: The `RagAgent` class initializes an agent using the `pydantic-ai` library and a Gemini model. It equips the agent with a single tool: `query_knowledge_base`. When a user asks a question, the agent first uses this tool.
- **Retrieval**: The tool takes the user's query, generates a vector embedding for it, and performs a similarity search against the LanceDB database to find the top 5 most relevant chunks.
- **Generation**: The retrieved chunks are compiled into a context block, which is then passed to the Gemini model along with the original question. The model synthesizes this information to generate a comprehensive answer.
- **Output**: The agent streams the final answer to the console. The response includes the synthesized information, relevant code examples, and the source URLs from which the information was retrieved.

## Command-Line Interface (CLI) Usage

The entire pipeline is orchestrated via `main.py`.

### 1. Scrape a Website

Scrapes a website and stores the content as Markdown files.

```bash
python main.py scrape <workdir> <url> [--exclude /path1 /path2 ...]
```
- `workdir`: The directory to store the output `.md` files.
- `url`: The base URL to begin scraping from.
- `--exclude`: (Optional) A space-separated list of URL paths to exclude.

### 2. Chunk the Scraped Content

Converts the Markdown files into structured JSON chunk files.

```bash
python main.py chunk <workdir>
```
- `workdir`: The directory containing the `.md` files to process.

### 3. Embed the Chunks

Creates a LanceDB vector database from the JSON chunk files.

```bash
python main.py embed <dbfile> <pattern> --collection <name>
```
- `dbfile`: The path to the LanceDB database directory.
- `pattern`: A glob pattern to find the input `.json` chunk files (e.g., `"./data/*.json"`).
- `--collection`: The name of the table to create within the database.

### 4. Chat with the Agent

Starts the interactive chat agent.

```bash
python main.py agent <dbfile> --collection <name>
```
- `dbfile`: The path to the LanceDB database.
- `--collection`: The name of the collection to query.