import os
import requests

JINA_API_KEY = os.getenv("JINA_API_KEY", "")

class LinkExtractor:
    # Add **kwargs to allow it to ignore extra arguments like 'extension'
    def extract(self, url: str, **kwargs) -> dict:
        """
        Uses Jina Reader API to bypass React/JS mess and get clean text.
        """
        try:
            # Prefix the URL with r.jina.ai/
            jina_url = f"https://r.jina.ai/{url}"
            
            import random
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {JINA_API_KEY}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "X-Forwarded-For": f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}",
                "Accept-Language": "en-US,en;q=0.9"
            }
            
            response = requests.get(jina_url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                return self._fallback(url)

            data = response.json().get('data', {})
            content = data.get('content', "")
            title = data.get('title', "Webpage")

            return {
                "raw_text": content,
                "metadata": {
                    "file_type": "url",
                    "title": title,
                    "extraction_status": "success"
                }
            }
        except Exception as e:
            print(f"URL Extract Error: {e}")
            return self._fallback(url)

    def _fallback(self, url: str) -> dict:
        return {
            "raw_text": "",
            "metadata": {
                "file_type": "url",
                "title": "",
                "extraction_status": "failed"
            }
        }
