import argparse
from dotenv import load_dotenv
from rag_url.chunk import MarkdownChunker
from rag_url.scrape import BaseUrlScraper

# example
# python main.py scrape https://ai.pydantic.dev/ ./data/pydantic_ai/pages --exclude /api /img /llms.txt /llms-full.txt
# python main.py chunk ./data/pydantic_ai/pages ./data/pydantic_ai/chunks

load_dotenv()


def main():
    parser = argparse.ArgumentParser(prog="rag url")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Scrape command
    scrape_parser = subparsers.add_parser("scrape", help="Scrape a base url")
    scrape_parser.add_argument("url", type=str, help="Target base url to scrape from")
    scrape_parser.add_argument("outdir", type=str, help="Output directory")
    scrape_parser.add_argument(
        "--delay", type=float, default=0.1, help="Delay between requests (in seconds)"
    )
    scrape_parser.add_argument(
        "--exclude", nargs="*", default=[], help="List of paths to exclude"
    )

    # Chunk command
    chunk_parser = subparsers.add_parser("chunk", help="Chunk the scraped pages")
    chunk_parser.add_argument("indir", type=str, help="Input directory of md files")
    chunk_parser.add_argument("outdir", type=str, help="Output directory")
    chunk_parser.add_argument(
        "--delay", type=float, default=1.0, help="Delay between requests (in seconds)"
    )

    # parse and execute the command.
    args = parser.parse_args()

    if args.command == "scrape":
        BaseUrlScraper(args.url, args.outdir, args.delay, args.exclude).run()
    elif args.command == "chunk":
        MarkdownChunker(args.indir, args.outdir, args.delay).run()
    else:
        raise Exception("Unexpected input")


if __name__ == "__main__":
    main()
