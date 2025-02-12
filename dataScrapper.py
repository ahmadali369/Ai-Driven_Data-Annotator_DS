import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

class WebCrawler:
    def __init__(self, base_urls, max_downloads=1000):
        self.base_urls = base_urls
        self.visited = set()
        self.downloaded_count = 0
        self.max_downloads = max_downloads

    def crawl(self, url, year_folder):
        if url in self.visited or self.downloaded_count >= self.max_downloads:
            return
        print(f"Crawling: {url}")
        self.visited.add(url)

        try:
            response = requests.get(url)
            if 'text/html' in response.headers['Content-Type']:
                soup = BeautifulSoup(response.content, 'html.parser')
                links = soup.find_all('a', href=True)
                for link in links:
                    if self.downloaded_count >= self.max_downloads:
                        return
                    next_url = urljoin(url, link['href'])
                    if next_url.lower().endswith('.pdf'):
                        self.download_pdf(next_url, year_folder)
                    elif urlparse(next_url).netloc == urlparse(url).netloc:
                        self.crawl(next_url, year_folder)
            else:
                print(f"Skipping non-HTML content at {url}")
        except Exception as e:
            print(f"Failed to crawl {url}: {e}")

    def download_pdf(self, url, year_folder):
        if self.downloaded_count >= self.max_downloads:
            return
        try:
            pdf_name = os.path.basename(url)
            pdf_path = os.path.join(year_folder, pdf_name)
            print(f"Downloading {pdf_name}...")
            response = requests.get(url)
            with open(pdf_path, 'wb') as f:
                f.write(response.content)
            self.downloaded_count += 1
            print(f"Downloaded: {pdf_name} ({self.downloaded_count}/{self.max_downloads})")
        except Exception as e:
            print(f"Failed to download {url}: {e}")

    def start_crawl(self):
        for base_url in self.base_urls:
            if self.downloaded_count >= self.max_downloads:
                break
            year = base_url.split('/')[-1]
            year_folder = f"NeurIPS_{year}"
            os.makedirs(year_folder, exist_ok=True)
            print(f"Starting crawl for {year}...")
            self.crawl(base_url, year_folder)
        print(f"Crawling complete. Total PDFs downloaded: {self.downloaded_count}")

# List of URLs to start crawling from
base_urls = [
    f"https://proceedings.neurips.cc/paper/{year}" for year in range(2024, 1986, -1)
]

if __name__ == "__main__":
    crawler = WebCrawler(base_urls)
    crawler.start_crawl()
