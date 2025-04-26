import json
import pytest
from unittest.mock import AsyncMock, MagicMock

def mock_llm_chain(return_value_dict: dict):
    """Create a mocked LangChain-style LLM chain with a JSON string response."""
    mock_response = MagicMock()
    mock_response.content = json.dumps(return_value_dict)

    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = mock_response

    return mock_chain