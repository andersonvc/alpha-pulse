"""EDGAR API client for querying/formatting SEC filings. Uses SECClient for rate limiting."""

import asyncio
from typing import List
import pandas as pd
import logging
from alpha_pulse.tools.edgar.sec_client import SECClient
from alpha_pulse.tools.edgar.utils import parse_atom_latest_filings_feed
from alpha_pulse.agent_workflows import run_doc_analysis
from alpha_pulse.storage.edgar_db_client import EdgarDBClient
from alpha_pulse.types.dbtables.filing_entry import FilingRSSFeedEntry
from alpha_pulse.tools.edgar.utils import extract_8k_url_from_base_url, clean_and_extract_normalized_sections, parse_document_string, extract_exhibit_number
from alpha_pulse.types.dbtables.parsed_8k_text import Parsed8KText
from alpha_pulse.types.dbtables.parsed_ex99_text import ParsedEX99Text
from alpha_pulse.types.dbtables.analyzed_ex99_text import DocAnalysis, AnalyzedEX99Text
from alpha_pulse.types.dbtables.parsed_items import Item502Summary
from alpha_pulse.agent_workflows.parse_8k_502 import run_502_graph
from alpha_pulse.storage.publishers.publish_parsed_502 import publish_parsed_502
from alpha_pulse.agent_workflows.item801_analyzer import run_item801_analysis
from alpha_pulse.types.dbtables.analyzed_801_text import FullAnalysis, Analyzed801Text
from alpha_pulse.storage.publishers.publish_parsed_801 import publish_parsed_801
class EdgarClient:
    """Client for querying/formatting SEC filings."""

    def __init__(self):
        self.client = SECClient()
        self.db_handler = EdgarDBClient()
        self.db_handler._startup_db()

    async def grab_recent_filings(self, filing_type: str, limit: int = 100, start=0) -> list[dict]:
        """Get list of 8k filings based on filter criteria."""
        
        if start >= 200:
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
                    item_text=item_text,
                    urls_ex99=rec.url_ex99
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

        # Parse 502 text
        async def parse_502_text(rec:Parsed8KText):
            print(f"Parsing {rec.item_number} text for {rec.cik} {rec.filing_date} {rec.item_number}")
            if rec.item_number == '5.02':

                text = rec.item_text
                results:Item502Summary = await run_502_graph(text)
                await publish_parsed_502(rec, results)
            elif rec.item_number == '8.01':
                text = rec.item_text
                results:FullAnalysis = await run_item801_analysis(text)
                record:Analyzed801Text = Analyzed801Text(
                    cik=rec.cik,
                    filing_date=rec.filing_date,
                    item_number=rec.item_number,
                    base_url=rec.base_url,
                    ts=rec.ts,
                    **results.model_dump()
                )
                await publish_parsed_801(record)
        
        tasks = [parse_502_text(rec) for rec in unique_text_recs]
        await asyncio.gather(*tasks)

        
        unique_ex99_recs = {}
        for rec in unique_text_recs:
            if rec.urls_ex99:
                urls = rec.urls_ex99.split(',')
                for i,url in enumerate(urls):
                    if not url.endswith('.htm'):
                        continue
                    #ex99_id = extract_exhibit_number(url)
                    #if not ex99_id:
                    #    continue
                    ex99_id = str(i)

                    key = (rec.cik,rec.filing_date,ex99_id)
                    if key in unique_ex99_recs:
                        continue

                    parsed_ex99_text = await self.client._make_request(url)
                    parsed_ex99_text = parse_document_string(parsed_ex99_text)

                    unique_ex99_recs[key] = ParsedEX99Text(
                        cik=rec.cik,
                        ex99_id=ex99_id,
                        ex99_url=url,
                        base_url=rec.base_url,
                        ex99_text=parsed_ex99_text,
                        ts=rec.ts,
                        filing_date=rec.filing_date
                    )
        unique_ex99_recs: List[ParsedEX99Text] = list(unique_ex99_recs.values())

        # Analyze ex99 text
        async def analyze_ex99_text(rec:ParsedEX99Text):
            res_partial:DocAnalysis = await run_doc_analysis(rec.ex99_text)
            res_full = AnalyzedEX99Text(
                cik=rec.cik,
                filing_date=rec.filing_date,
                ex99_id=rec.ex99_id,
                ex99_url=rec.ex99_url,
                ts=rec.ts,
                **res_partial.model_dump()
            )
            return res_full

        tasks = [analyze_ex99_text(rec) for rec in unique_ex99_recs]
        res_fulls = await asyncio.gather(*tasks)
        res_fulls = [rec for rec in res_fulls if rec is not None]

        self.db_handler.insert_records('parsed_8k_text', unique_text_recs)
        self.db_handler.insert_records('parsed_ex99_text', unique_ex99_recs)
        self.db_handler.insert_records('analyzed_ex99_text', res_fulls)
        
        # set all records as processed
        self.db_handler.update_processed_filings([rec.base_url for rec in recs])


async def main():
    client = EdgarClient()
    await client.grab_recent_filings('8-K')
    await client.parse_filings()

if __name__ == '__main__':
    asyncio.run(main())

