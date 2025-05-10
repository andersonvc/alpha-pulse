
import logging
import asyncio
from alpha_pulse.clients.sec.sec_client import SECClient
from alpha_pulse.storage.edgar_db_client import EdgarDBClient
from alpha_pulse.clients.edgar.utils import parse_atom_latest_filings_feed, ALLOWED_8K_ITEMS
from alpha_pulse.clients.edgar.filing_downloader import FilingDownloader
from alpha_pulse.clients.edgar.filing_parser import FilingParser
from alpha_pulse.clients.edgar.item_analyzer import ItemAnalyzer
from alpha_pulse.clients.edgar.exhibit_analyzer import ExhibitAnalyzer


class EdgarClient:
    def __init__(self):
        self.client = SECClient()
        self.db = EdgarDBClient()
        self.db._startup_db()

        self.downloader = FilingDownloader(self.client, self.db)
        self.parser = FilingParser()
        self.item_analyzer = ItemAnalyzer()
        self.exhibit_analyzer = ExhibitAnalyzer(self.client, self.db)

    async def grab_recent_filings(self, filing_type: str, limit: int = 100, start: int = 0, stop_early: bool=True):
        if start >= 1000:
            return

        url = f"{self.client.base_url}/cgi-bin/browse-edgar?company=&CIK=&type={filing_type}&start={start}&count={limit}&action=getcurrent&output=atom"
        logging.info(f"Fetching filings from {url}")

        resp = await self.client._make_request(url, self.client.headers)
        filings = parse_atom_latest_filings_feed(resp)

        new_filing_urls = [f.base_url for f in filings]
        unseen = self.db.filter_out_existing_primary_keys('filed_8k_listing', new_filing_urls)
        new_filings = [f for f in filings if f.base_url in unseen]

        from alpha_pulse.tools.polygon.company_info import get_ticker_by_cik, get_market_cap_by_ticker, get_sic_by_ticker

        for filing in new_filings:
            filing.ticker = await get_ticker_by_cik(filing.cik)
            filing.market_cap = await get_market_cap_by_ticker(filing.ticker)
            filing.sic = await get_sic_by_ticker(filing.ticker)

        new_filings = [f for f in new_filings if f.market_cap >= 1.0 and f.item_list is not None]
        new_filings = [f for f in new_filings if set(f.item_list.split(',')) - ALLOWED_8K_ITEMS]

        if not new_filings and stop_early:
            logging.info(f"No new filings found for {filing_type} starting at {start}")
            return

        self.db.insert_records('filed_8k_listing', new_filings)
        logging.info(f"Inserted {len(new_filings)} new filings.")

        await self.grab_recent_filings(filing_type, limit, start + limit, stop_early)

    async def parse_filings(self):
        filings = self.db.get_unprocessed_filings()[:100]
        if not filings:
            logging.info("No new filings to parse")
            return

        await self.downloader.download(filings)
        parsed_texts = self.parser.parse(filings)

        await self.item_analyzer.analyze(parsed_texts)
        await self.exhibit_analyzer.analyze(parsed_texts)

        for record in parsed_texts:
            try:
                self.db.insert_records('parsed_8k_text', record)
            except Exception as e:
                logging.error(f"Error inserting parsed text: {record.cik} {record.filing_date} {record.item_number}")

        self.db.update_processed_filings([f.base_url for f in filings])
        await self.parse_filings()
