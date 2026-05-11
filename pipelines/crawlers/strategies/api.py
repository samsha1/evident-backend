import aiohttp
from pipelines.crawlers.core.base import CrawlStrategy

class ApiStrategy(CrawlStrategy):
    """Strategy for fetching data via HTTP APIs using aiohttp."""
    
    def __init__(self, base_url: str | None = None, headers: dict[str, str] | None = None):
        self.base_url = base_url
        self.headers = headers or {}

    async def fetch(
        self, 
        endpoint: str, 
        method: str = "GET",
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        data: dict[str, str] | None = None,
        json_data: dict[str, object] | None = None
    ) -> str:
        """Fetch raw data from the API.
        
        Args:
            endpoint: URL or relative path.
            method: HTTP method (GET, POST, etc.).
            headers: Optional headers to merge with defaults.
            params: Optional query parameters.
            data: Optional form data.
            json_data: Optional JSON body data.
        """
        req_headers = {**self.headers, **(headers or {})}
        
        url = endpoint
        if self.base_url and not endpoint.startswith("http"):
            url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
            
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method, 
                url, 
                headers=req_headers, 
                params=params, 
                data=data, 
                json=json_data
            ) as response:
                response.raise_for_status()
                return await response.text()
