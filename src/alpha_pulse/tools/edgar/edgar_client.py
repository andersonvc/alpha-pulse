"""EDGAR API client for querying/formatting SEC filings. Uses SECClient for rate limiting."""

import asyncio
from typing import List
import pandas as pd
import logging
from alpha_pulse.tools.edgar.sec_client import SECClient
from alpha_pulse.tools.edgar.utils import parse_atom_latest_filings_feed

from alpha_pulse.storage.edgar_db_client import EdgarDBClient
from alpha_pulse.types.dbtables.filing_entry import FilingRSSFeedEntry
from alpha_pulse.tools.edgar.utils import extract_8k_url_from_base_url, clean_and_extract_normalized_sections
from alpha_pulse.types.dbtables.parsed_8k_text import Parsed8KText



class EdgarClient:
    """Client for querying/formatting SEC filings."""

    def __init__(self):
        self.client = SECClient()
        self.db_handler = EdgarDBClient()
        self.db_handler._startup_db()

    async def grab_recent_filings(self, filing_type: str, limit: int = 100, start=0) -> list[dict]:
        """Get list of 8k filings based on filter criteria."""
        
        if start >= 1000:
            return

        url = f"{self.client.base_url}/cgi-bin/browse-edgar?company=&CIK=&type={filing_type}&owner=include&start={start}&count={limit}&action=getcurrent&output=atom"
        resp = await self.client._make_request(url, self.client.headers)
        recs: List[FilingRSSFeedEntry] = parse_atom_latest_filings_feed(resp)
        
        # filter out any records that are already in the database
        pkeys = [r.base_url for r in recs]
        new_indices = self.db_handler.filter_out_existing_primary_keys('filed_8k_listing', pkeys)
        
        filtered_recs = [rec for rec in recs if rec.base_url in new_indices]
        if len(filtered_recs) == 0:
            logging.info(f"No new filings found for {filing_type} at start {start}")
            return

        # write all recurds in df to db
        self.db_handler.insert_records('filed_8k_listing', filtered_recs)

        await self.grab_recent_filings(filing_type, limit, start+limit)
    
    async def parse_filings(self):
        """Parse all filings flagged as unprocessed in the database."""
        recs = self.db_handler.get_unprocessed_filings()

        async def load_base_url(rec:FilingRSSFeedEntry):
            html = await self.client._make_request(rec.base_url)
            url_8k,url_ex99 = extract_8k_url_from_base_url(html)
            rec.url_8k = url_8k
            rec.url_ex99 = url_ex99

            # get raw text of 8-K
            raw_8k_text = await self.client._make_request(url_8k)
            rec.raw_8k_text = raw_8k_text

            await self.db_handler.update_url_8k(rec.base_url, url_8k, url_ex99, raw_8k_text)
        
        tasks = [load_base_url(rec) for rec in recs]
        await asyncio.gather(*tasks)
        
        def parse_8k_text(rec:FilingRSSFeedEntry)->List[Parsed8KText]:
            item_text = clean_and_extract_normalized_sections(rec.raw_8k_text)
            results = []
            for item_number, item_text in item_text.items():
                results.append(Parsed8KText(
                    cik=rec.cik, 
                    filing_date=rec.filing_date, 
                    item_number=item_number, 
                    base_url=rec.base_url,
                    ts=rec.ts,
                    item_text=item_text
                ))
            return results
        
        text_recs = []
        for rec in recs:
            text_recs.extend(parse_8k_text(rec))
        text_recs = [rec for rec in text_recs if rec is not None]
        
        unique_text_recs = {}
        for rec in text_recs:
            unique_text_recs[(rec.cik,rec.filing_date,rec.item_number)] = rec
        unique_text_recs = list(unique_text_recs.values()) 
        
        self.db_handler.insert_records('parsed_8k_text', unique_text_recs)
        
        # set all records as processed
        self.db_handler.update_processed_filings([rec.base_url for rec in recs])


async def main():
    client = EdgarClient()
    await client.grab_recent_filings('8-K')
    await client.parse_filings()

if __name__ == '__main__':
    asyncio.run(main())

