import argparse
from dotenv import load_dotenv
from rag_url.chunk import MarkdownChunker
from rag_url.scrape import BaseUrlScraper

# example
# python main.py scrape https://ai.pydantic.dev/ ./data/pydantic_ai/pages --exclude /api /img /llms.txt /llms-full.txt

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

    args = parser.parse_args()

    if args.command == "scrape":
        BaseUrlScraper(args.url, args.exclude).run(args.outdir, args.delay)


if __name__ == "__main__":
    main()
