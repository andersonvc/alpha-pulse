import asyncio
import logging
from alpha_pulse.clients.edgar.edgar_client import EdgarClient

async def main():
    logging.basicConfig(level=logging.INFO)
    client = EdgarClient()
    await client.grab_recent_filings('8-K',stop_early=True)
    await client.parse_filings()


if __name__ == "__main__":
    asyncio.run(main())