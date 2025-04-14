import asyncio
import logging
from alpha_pulse.agents.edgar_8k_agent import Edgar8kAgent
from alpha_pulse.agents.edgar.agent_8k_parser import create_8k_parser_graph

async def main():
    logging.basicConfig(level=logging.INFO)
    ticker = 'META'
    graph = create_8k_parser_graph()
    graph({'ticker':ticker})
    #edgar_8k_agent = Edgar8kAgent()
    #filing = await edgar_8k_agent({'ticker':ticker})
    # print(filing)
    

if __name__ == "__main__":
    asyncio.run(main())