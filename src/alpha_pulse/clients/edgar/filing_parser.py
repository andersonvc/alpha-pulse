
from alpha_pulse.clients.edgar.utils import clean_and_extract_normalized_sections
from alpha_pulse.types.dbtables.parsed_8k_text import Parsed8KText

class FilingParser:
    def parse(self, filings):
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
