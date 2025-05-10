
from alpha_pulse.clients.edgar.utils import parse_document_string, SharedSingletonSet
from alpha_pulse.types.dbtables.parsed_ex99_text import ParsedEX99Text
from alpha_pulse.types.dbtables.analyzed_ex99_text import AnalyzedEX99Text
from alpha_pulse.agent_workflows import run_doc_analysis
import logging
import asyncio

class ExhibitAnalyzer:
    def __init__(self, client, db):
        self.client = client
        self.db = db
        self.exhibit_set = SharedSingletonSet()

    async def analyze(self, parsed_texts):
        tasks = []
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
                    tasks.append(self._download_and_parse_exhibit(url, parsed, str(idx)))

        exhibits = await asyncio.gather(*tasks)
        exhibits = list({(e.cik, e.filing_date, e.ex99_id): e for e in exhibits if e}.values())

        analyzed_exhibits = await asyncio.gather(*(self._analyze_exhibit_text(e) for e in exhibits))
        analyzed_exhibits = [e for e in analyzed_exhibits if e is not None]

        self.db.insert_records('parsed_ex99_text', exhibits)
        self.db.insert_records('analyzed_ex99_text', analyzed_exhibits)

    async def _download_and_parse_exhibit(self, url, parsed, ex99_id):
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

    async def _analyze_exhibit_text(self, exhibit):
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
