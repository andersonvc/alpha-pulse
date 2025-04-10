import asyncio

from alpha_pulse.agents.news_agent import NewsAgent

async def main():
    ticker = 'AAPL'
    news_agent = NewsAgent()
    news = await news_agent.analyze_news(ticker)
    print(news)

if __name__ == "__main__":
    asyncio.run(main())