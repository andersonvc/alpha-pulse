import os
from polygon import RESTClient


class PolygonClient:
    def __init__(self):
        api_key = os.getenv('POLYGON_API_KEY')
        self.client = RESTClient(api_key)

    async def get_symbol_for_cik(self, cik: str) -> str:
        entities = await self.client.async_list_tickers_v3(cik=cik)
        for entity in entities:
            return entity.symbol
        return None
    
    async def get_market_cap_by_ticker(self, ticker: str) -> float:
        details = await self.client.async_get_ticker_details_v3(ticker)
        return details.market_cap
    
    async def get_sic_by_ticker(self, ticker: str) -> str:
        details = await self.client.async_get_ticker_details_v3(ticker)
        return details.sic
    