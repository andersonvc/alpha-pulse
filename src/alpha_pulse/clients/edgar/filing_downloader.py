
from alpha_pulse.clients.sec.sec_client import SECClient
from alpha_pulse.storage.edgar_db_client import EdgarDBClient
from alpha_pulse.clients.edgar.utils import extract_8k_url_from_base_url
import logging
import asyncio

class FilingDownloader:
    def __init__(self, client: SECClient, db: EdgarDBClient):
        self.client = client
        self.db = db

    async def download(self, filings):
        async def download_one(filing):
            html = await self.client._make_request(filing.base_url)
            filing.url_8k, filing.url_ex99 = extract_8k_url_from_base_url(html)
            try:
                filing.raw_8k_text = await self.client._make_request(filing.url_8k)
            except Exception as e:
                logging.error(f"Error downloading 8-K text: {filing.url_8k}")
                logging.error(f"Error: {e}")
                return
            await self.db.update_url_8k(filing.base_url, filing.url_8k, filing.url_ex99, filing.raw_8k_text)

        await asyncio.gather(*(download_one(f) for f in filings))
