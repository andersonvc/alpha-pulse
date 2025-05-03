import asyncio
import logging
from typing import List

import pandas as pd

from alpha_pulse.tools.edgar.sec_client import SECClient
from alpha_pulse.tools.edgar.utils import (
    parse_atom_latest_filings_feed,
    extract_8k_url_from_base_url,
    clean_and_extract_normalized_sections,
    parse_document_string,
)
from alpha_pulse.types.dbtables.filing_entry import FilingRSSFeedEntry
from alpha_pulse.types.dbtables.parsed_8k_text import Parsed8KText
from alpha_pulse.types.dbtables.parsed_ex99_text import ParsedEX99Text
from alpha_pulse.types.dbtables.analyzed_ex99_text import AnalyzedEX99Text
from alpha_pulse.types.dbtables.analyzed_801_text import Analyzed801Text
from alpha_pulse.types.dbtables.parsed_items import Item502Summary
from alpha_pulse.agent_workflows import run_doc_analysis
from alpha_pulse.agent_workflows.parse_8k_502 import run_502_graph
from alpha_pulse.agent_workflows.item801_analyzer import run_item801_analysis
from alpha_pulse.storage.edgar_db_client import EdgarDBClient
from alpha_pulse.storage.publishers.publish_parsed_502 import publish_parsed_502
from alpha_pulse.storage.publishers.publish_parsed_801 import publish_parsed_801
from alpha_pulse.tools.edgar.utils import SharedSingletonSet
from alpha_pulse.tools.polygon.company_info import get_ticker_by_cik, get_market_cap_by_ticker, get_sic_by_ticker
from alpha_pulse.tools.edgar.utils import ALLOWED_8K_ITEMS


class EdgarClient:
    """Client for downloading and parsing SEC 8-K filings."""

    def __init__(self):
        self.client = SECClient()
        self.db = EdgarDBClient()
        self.db._startup_db()
        self.exhibit_set = SharedSingletonSet()

    async def grab_recent_filings(self, filing_type: str, limit: int = 100, start: int = 0, stop_early: bool=True):
        """Recursively fetch recent filings of a given type."""
        print(start)
        if start >= 1000:
            return

        url = f"{self.client.base_url}/cgi-bin/browse-edgar?company=&CIK=&type={filing_type}&start={start}&count={limit}&action=getcurrent&output=atom"
        logging.info(f"Fetching filings from {url}")

        resp = await self.client._make_request(url, self.client.headers)
        filings: List[FilingRSSFeedEntry] = parse_atom_latest_filings_feed(resp)

        # Filter out already processed
        new_filing_urls = [f.base_url for f in filings]
        unseen = self.db.filter_out_existing_primary_keys('filed_8k_listing', new_filing_urls)
        new_filings = [f for f in filings if f.base_url in unseen]

        # For each new filing, get and include the company info
        for filing in new_filings:
            filing.ticker = await get_ticker_by_cik(filing.cik)
            filing.market_cap = await get_market_cap_by_ticker(filing.ticker)
            filing.sic = await get_sic_by_ticker(filing.ticker)
        new_filings = [f for f in new_filings if f.market_cap >= 1.0]
        new_filings = [f for f in new_filings if f.item_list is not None]
        new_filings2 = []
        for filing in new_filings:
            item_list = set(filing.item_list.split(','))
            if item_list - ALLOWED_8K_ITEMS:
                new_filings2.append(filing)
        new_filings = new_filings2

        if not new_filings and stop_early:
            logging.info(f"No new filings found for {filing_type} starting at {start}")
            return

        self.db.insert_records('filed_8k_listing', new_filings)
        logging.info(f"Inserted {len(new_filings)} new filings.")

        # Recursive fetch
        await self.grab_recent_filings(filing_type, limit, start + limit,stop_early)

    async def parse_filings(self):
        """Parse new, unprocessed filings."""
        filings = self.db.get_unprocessed_filings()
        filings = filings[:100]
        if not filings:
            logging.info("No new filings to parse")
            return

        await self._download_filing_texts(filings)
        parsed_texts = self._parse_8k_sections(filings)


        await self._analyze_item_sections(parsed_texts)
        await self._analyze_exhibits(parsed_texts)

        for record in parsed_texts:
            try:
                self.db.insert_records('parsed_8k_text', record)
            except Exception as e:
                logging.error(f"Error inserting parsed texts: {record.cik} {record.filing_date} {record.item_number}")
        self.db.update_processed_filings([f.base_url for f in filings])

        await self.parse_filings()

    

    async def _download_filing_texts(self, filings: List[FilingRSSFeedEntry]):
        """Load 8-K and EX-99 URLs and content."""
        async def download(filing: FilingRSSFeedEntry):
            html = await self.client._make_request(filing.base_url)
            filing.url_8k, filing.url_ex99 = extract_8k_url_from_base_url(html)
            try:
                filing.raw_8k_text = await self.client._make_request(filing.url_8k)
            except Exception as e:
                logging.error(f"Error downloading 8-K text: {filing.url_8k}")
                logging.error(f"Error: {e}")
                return
            await self.db.update_url_8k(filing.base_url, filing.url_8k, filing.url_ex99, filing.raw_8k_text)

        await asyncio.gather(*(download(f) for f in filings))

    def _parse_8k_sections(self, filings: List[FilingRSSFeedEntry]) -> List[Parsed8KText]:
        """Split filings into Parsed8KText entries."""
        parsed = []
        for filing in filings:
            sections = clean_and_extract_normalized_sections(filing.raw_8k_text)
            for item, text in sections.items():
                parsed.append(Parsed8KText(
                    cik=filing.cik,
                    filing_date=filing.filing_date,
                    item_number=item,
                    base_url=filing.base_url,
                    ts=filing.ts,
                    item_text=text,
                    urls_ex99=filing.url_ex99
                ))
        return parsed

    async def _analyze_item_sections(self, parsed_texts: List[Parsed8KText]):
        """Analyze items like 5.02 (appointments) and 8.01 (general info)."""
        async def analyze(text: Parsed8KText):
            if text.item_number == '5.02':
                summary = await run_502_graph(text.item_text)
                await publish_parsed_502(text, summary)
            elif text.item_number == '8.01':
                analysis = await run_item801_analysis(text.item_text)
                await publish_parsed_801(Analyzed801Text(
                    cik=text.cik,
                    filing_date=text.filing_date,
                    item_number=text.item_number,
                    base_url=text.base_url,
                    ts=text.ts,
                    **analysis.model_dump()
                ))

        await asyncio.gather(*(analyze(t) for t in parsed_texts))

    async def _analyze_exhibits(self, parsed_texts: List[Parsed8KText]):
        """Analyze EX-99 exhibit texts."""
        ex99_tasks = []
        unique_exhibits = {}

        for parsed in parsed_texts:
            if not parsed.urls_ex99:
                continue
            urls = parsed.urls_ex99.split(',')
            for idx, url in enumerate(urls):
                if not url.endswith('.htm'):
                    continue
                key = (parsed.cik, parsed.filing_date, str(idx))
                if key not in unique_exhibits and not self.db.record_exists('parsed_ex99_text', key) and url not in self.exhibit_set.get_all():
                    self.exhibit_set.add(url)
                    ex99_tasks.append(self._download_and_parse_exhibit(url, parsed, str(idx)))


        exhibits = await asyncio.gather(*ex99_tasks)
        exhibits = list({(e.cik, e.filing_date, e.ex99_id): e for e in exhibits if e}.values())

        analyzed_exhibits = await asyncio.gather(*(self._analyze_exhibit_text(e) for e in exhibits))
        analyzed_exhibits = [e for e in analyzed_exhibits if e is not None]

        self.db.insert_records('parsed_ex99_text', exhibits)
        self.db.insert_records('analyzed_ex99_text', analyzed_exhibits)

    async def _download_and_parse_exhibit(self, url: str, parsed: Parsed8KText, ex99_id: str) -> ParsedEX99Text:
        try:
            text = await self.client._make_request(url)
            parsed_text = parse_document_string(text)
        except Exception as e:
            logging.error(f"Error downloading and parsing exhibit: {url}")
            logging.error(f"Error: {e}")
            return None
        return ParsedEX99Text(
            cik=parsed.cik,
            filing_date=parsed.filing_date,
            ex99_id=ex99_id,
            ex99_url=url,
            base_url=parsed.base_url,
            ts=parsed.ts,
            ex99_text=parsed_text
        )

    async def _analyze_exhibit_text(self, exhibit: ParsedEX99Text) -> AnalyzedEX99Text:
        try:
            analysis = await run_doc_analysis(exhibit.ex99_text)
            return AnalyzedEX99Text(
                cik=exhibit.cik,
                filing_date=exhibit.filing_date,
                ex99_id=exhibit.ex99_id,
                ex99_url=exhibit.ex99_url,
                ts=exhibit.ts,
                **analysis.model_dump()
            )
        except Exception as e:
            logging.error(f"Error analyzing exhibit text: {exhibit.ex99_url}")
            logging.error(f"Exhibit text: {exhibit.ex99_text}")
            return None


async def main():
    logging.basicConfig(level=logging.INFO)
    client = EdgarClient()
    await client.grab_recent_filings('8-K',stop_early=False)
    await client.parse_filings()


if __name__ == "__main__":
    asyncio.run(main())
