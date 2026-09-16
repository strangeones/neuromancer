import requests
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

class ScraperConstruct:
    """Construct for scraping websites or internal router config pages."""
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Tessier-Ashpool Construct/1.0)"
        })

    def scrape(self, url: str) -> dict:
        """Fetches a URL and extracts visible text and links."""
        result = {"url": url, "text": "", "links": []}
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Kill javascript and style blocks
            for script in soup(["script", "style"]):
                script.extract()
                
            text = soup.get_text(separator='\n')
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            result["text"] = '\n'.join(chunk for chunk in chunks if chunk)[:2000] # Limit to 2k chars for LLM
            
            # Extract up to 20 links
            for a in soup.find_all('a', href=True)[:20]:
                result["links"].append(a['href'])
                
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            result["error"] = str(e)
            
        return result
