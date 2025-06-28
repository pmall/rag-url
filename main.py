import argparse
from dotenv import load_dotenv
from rag_url.agent import RagAgent
from rag_url.embed import ChunkEmbedder
from rag_url.chunk import MarkdownChunker
from rag_url.scrape import BaseUrlScraper

# example
# python main.py scrape ./data/pydantic_ai https://ai.pydantic.dev/ --exclude /api /img /llms.txt /llms-full.txt
# python main.py chunk ./data/pydantic_ai
# python main.py embed ./data/_lancedb "./data/pydantic_ai/*.json" --collection pydantic_ai

load_dotenv()


def main():
    parser = argparse.ArgumentParser(prog="rag url")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Scrape command
    scrape_parser = subparsers.add_parser("scrape", help="Scrape a base url")
    scrape_parser.add_argument(
        "workdir", type=str, help="The directory where to store markdown files"
    )
    scrape_parser.add_argument("url", type=str, help="The base url to scrape from")
    scrape_parser.add_argument(
        "--delay", type=float, default=0.1, help="Delay between requests (in seconds)"
    )
    scrape_parser.add_argument(
        "--exclude", nargs="*", default=[], help="List of paths to exclude"
    )

    # Chunk command
    chunk_parser = subparsers.add_parser("chunk", help="Chunk the scraped pages")
    chunk_parser.add_argument(
        "workdir", type=str, help="The directory with markdown files to chunk"
    )
    chunk_parser.add_argument(
        "--delay", type=float, default=1.0, help="Delay between requests (in seconds)"
    )

    # Embed command
    embed_parser = subparsers.add_parser("embed", help="embed json chunk files")
    embed_parser.add_argument("dbfile", type=str, help="The persisent db file")
    embed_parser.add_argument(
        "pattern", type=str, help="The glob pattern to collect json chunk files"
    )
    embed_parser.add_argument(
        "--collection",
        type=str,
        required=True,
        help="Collection storing the embeddings in the db",
    )

    # Agent command
    agent_parser = subparsers.add_parser("agent", help="Run the RAG agent")
    agent_parser.add_argument("dbfile", type=str, help="The persistent db file")
    agent_parser.add_argument(
        "--collection",
        type=str,
        required=True,
        help="Collection storing the embeddings in the db",
    )

    # parse and execute the command.
    args = parser.parse_args()

    if args.command == "scrape":
        BaseUrlScraper(args.workdir, args.url, args.delay, args.exclude).run()
    elif args.command == "chunk":
        MarkdownChunker(args.workdir, args.delay).run()
    elif args.command == "embed":
        ChunkEmbedder(args.dbfile, args.pattern, args.collection).run()
    elif args.command == "agent":
        RagAgent(args.dbfile, args.collection).run()
    else:
        raise Exception("Unexpected input")


if __name__ == "__main__":
    main()
