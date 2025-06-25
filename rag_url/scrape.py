import re
import time
import requests
import trafilatura
from typing import Any
from pathlib import Path
from bs4 import BeautifulSoup, Tag
from urllib.parse import urlparse, urljoin


class BaseUrlScraper:
    def __init__(
        self,
        workdir: str,
        base_url: str,
        delay: float = 0.1,
        excluded_paths: list[str] | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.workdir = workdir
        self.delay = delay
        self.excluded_paths = [url.rstrip("/") for url in excluded_paths or []]

    def _is_valid_url(self, url: str) -> bool:
        parsed_base = urlparse(self.base_url)
        parsed_url = urlparse(url.rstrip("/"))

        if parsed_url.fragment:
            return False

        if not parsed_base.netloc == parsed_url.netloc:
            return False

        return not any([parsed_url.path.startswith(e) for e in self.excluded_paths])

    def _url_to_filename(self, url):
        """Convert URL to a safe filepath"""
        parsed = urlparse(url)
        path = parsed.path.strip("/")

        if not path or path == "":
            filename = "index"
        else:
            # Replace path separators and invalid characters
            filename = re.sub(r"[^\w\-_.]", "_", path.replace("/", "_"))
            filename = re.sub(r"_+", "_", filename).strip("_")

        return f"{filename}.md"

    def _extract_urls(self, url: str, soup: BeautifulSoup) -> list[str]:
        urls = set()

        for link in soup.find_all("a", href=True):
            if isinstance(link, Tag):
                href = link.get("href")
                if isinstance(href, str):
                    urls.add(urljoin(url, href))

        return list(urls)

    def _clean_markup(self, soup: BeautifulSoup) -> str:
        # No need the links for a rag system.
        for link in soup.find_all("a"):
            if isinstance(link, Tag):
                link.unwrap()

        return str(soup)

    def _to_markdown(self, url: str, content: Any) -> str:
        markdown = trafilatura.extract(
            content,
            output_format="markdown",
            include_links=True,
            include_images=True,
            include_tables=True,
        )

        if not markdown:
            raise Exception("Unable to parse page content as markdown.")

        return "\n".join(["---", f"url: {url}", "---", "", markdown])

    def _empty_workdir(self, workpath: Path):
        for file in workpath.iterdir():
            if file.is_file():
                file.unlink()

    def run(self) -> None:
        found_urls = set()
        workpath = Path(self.workdir)
        queue = [self.base_url]

        session = requests.Session()
        session.headers.update({"User-Agent": "rag-url/1.0"})

        if not workpath.exists():
            raise Exception(f"Workdir {workpath} does not exist")

        self._empty_workdir(workpath)

        while queue:
            current_url = queue.pop().rstrip("/")

            if current_url in found_urls:
                continue

            if not self._is_valid_url(current_url):
                continue

            print(current_url)

            found_urls.add(current_url)

            try:
                # get the page content.
                response = session.get(current_url)
                response.raise_for_status()

                # parse with beautiful soup.
                soup = BeautifulSoup(response.content, "html.parser")

                # extract all urls and queue unknown ones.
                for url in self._extract_urls(current_url, soup):
                    if not url in found_urls:
                        queue.append(url)

                # get a cleaned markup.
                markup = self._clean_markup(soup)

                # convert the markup to markdown.
                markdown = self._to_markdown(current_url, markup)

                # get a filename from the url.
                filename = self._url_to_filename(current_url)

                # finally write the file.
                with open(workpath / filename, "w", encoding="utf-8") as f:
                    f.write(markdown)

            except Exception as e:
                print(f"[ERROR] error scraping url {current_url}: {e}")

            time.sleep(self.delay)
