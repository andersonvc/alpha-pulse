# Alpha-Pulse: Intelligent SEC 8-K Parser for Financial Modeling

Alpha-Pulse is an LLM-powered agent system that automatically connects to the [SEC EDGAR](https://www.sec.gov/edgar.shtml) database, extracts and parses 8-K filings, and returns structured, context-aware outputs designed for seamless integration into financial models and investment analysis workflows.

---

## Overview

Manually parsing SEC filings is time-consuming and error-prone. Alpha-Pulse automates this process using Large Language Models (LLMs) that understand the nuances of financial disclosures. Given any publicly traded company, the agent fetches the latest 8-K filing, interprets the content using domain-specific reasoning, and structures the output for downstream processing.

---

## Key Features

- **Automatic EDGAR Integration**: Fetches the latest 8-K filings using EDGAR's API or RSS feeds.  
- **LLM-Powered Understanding**: Uses custom LLM agents trained for financial disclosure analysis.  
- **Structured Output**: Parses item numbers, materiality, sentiment, and expectations into JSON for easy integration.  
- **Model-Ready Data**: Designed for use in financial models, dashboards, or automated alert systems.  
- **Multi-Company Context**: Identifies and includes related companies referenced in the filing.  

---

## Example Output

Here’s an example of Alpha-Pulse retrieving / parsing the latest 8-K filing for **S&P Global Inc.**:

script:
```bash
./alpha-pulse/run-workflow "S&P Global"
```

output:
```json
{
  "summary": "S&P Global Inc. announced the sale of its joint venture OSTTRA with CME Group Inc. through a press release.",
  "related_companies": ["CME Group Inc."],
  "items": [
    {
      "item_number": "7.01",
      "event_expected": "expected",
      "event_expected_rationale": "Companies often restructure their joint ventures based on strategic goals, making such sales a common occurrence.",
      "event_material": "material",
      "event_material_rationale": "The sale of a joint venture is a significant event that can impact the company's financial position and operations.",
      "event_sentiment": "neutral",
      "event_sentiment_rationale": "The sale of a joint venture can be seen as a strategic move but does not inherently indicate a positive or negative outcome for the company."
    },
    {
      "item_number": "9.01",
      "event_expected": "expected",
      "event_expected_rationale": "Filing exhibits is a routine part of SEC reporting requirements.",
      "event_material": "non-material",
      "event_material_rationale": "The inclusion of standard exhibits does not significantly impact the company's financials or operations.",
      "event_sentiment": "neutral",
      "event_sentiment_rationale": "The inclusion of exhibits is standard practice in 8-K filings and does not carry sentiment."
    }
  ]
}
```
