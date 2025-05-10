import asyncio
from alpha_pulse.types.dbtables.analyzed_801_text import Analyzed801Text
from alpha_pulse.agent_workflows import run_doc_analysis
from alpha_pulse.agent_workflows.parse_8k_502 import run_502_graph
from alpha_pulse.agent_workflows.item801_analyzer import run_item801_analysis
from alpha_pulse.storage.publishers.publish_parsed_502 import publish_parsed_502
from alpha_pulse.storage.publishers.publish_parsed_801 import publish_parsed_801

class ItemAnalyzer:
    async def analyze(self, parsed_texts):
        async def analyze_one(text):
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
        await asyncio.gather(*(analyze_one(t) for t in parsed_texts))
