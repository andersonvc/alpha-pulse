"""Unit tests for 8-K analysis agents."""

import json
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import pandas as pd

from alpha_pulse.agents.edgar.agent_8k_parser import Agent8KParser
from alpha_pulse.agents.edgar.agent_8k_801_analyzer import Agent8KAnalyzer_801
from alpha_pulse.types.edgar8k import State8K, Item8K_801
from tests.conftest import mock_llm_chain

@pytest.fixture
def sample_8k_text():
    """Sample 8-K filing text for testing."""
    return """
    Item 8.01 Other Events.
    
    On January 1, 2024, Company XYZ announced a strategic partnership with ABC Corp.
    The partnership will focus on developing new technologies in the AI space.
    The company expects this partnership to have a positive impact on future revenue.
    """

@pytest.fixture
def sample_state(sample_8k_text):
    """Create a sample State8K instance for testing."""
    return State8K(
        cik="0001234567",
        filing_date="2024-01-01",
        raw_text=sample_8k_text,
        items="8.01",
        parsed_items={}
    )

@pytest.fixture
def mock_llm():
    """Create a mock LLM for testing."""
    mock = Mock()
    mock.invoke.return_value = {
        "event_type": "Strategic Restructuring",
        "sentiment": 1,
        "event_summary": "Company announced strategic partnership",
        "key_takeaway": "Positive impact on future revenue",
        "probable_price_move": True,
        "price_move_reason": "Strategic partnership in AI space",
        "is_financially_material": True,
        "is_operational_impact": True,
        "is_related_to_prior": False,
        "is_recent_event": True,
        "unexpected_timing": False,
        "mentioned_companies": "ABC Corp",
        "mentioned_tickers": "",
        "keywords": "partnership, AI, technology",
        "strategic_signal": True,
        "priority_shift_detected": True
    }
    return mock

class TestAgent8KParser:
    """Test cases for Agent8KParser."""
    
    def test_init(self):
        """Test agent initialization."""
        agent = Agent8KParser()
        assert agent is not None
    
    @pytest.mark.asyncio
    @patch("alpha_pulse.agents.edgar.agent_8k_parser.ChatPromptTemplate")
    @patch("alpha_pulse.agents.edgar.agent_8k_parser.ChatOpenAI")
    async def test_call(self, mock_openai_class, mock_prompt_class, sample_state):
        # Use the helper to get a mock chain that returns JSON content
        mock_chain = mock_llm_chain({
            "8.01": "Parsed text content"
        })

        # Setup prompt | model chain
        mock_prompt = MagicMock()
        mock_prompt.__or__.return_value = mock_chain
        mock_prompt_class.from_messages.return_value = mock_prompt

        mock_model = MagicMock()
        mock_openai_class.return_value.with_structured_output.return_value = mock_model

        # Run the agent
        agent = Agent8KParser()
        result = await agent(sample_state)

        # Assert the expected output
        assert isinstance(result, State8K)
        assert "8.01" in result.parsed_items
        assert result.parsed_items["8.01"].parsed_text == "Parsed text content"

    
    @pytest.mark.asyncio
    async def test_call_with_invalid_state(self):
        """Test agent call with invalid state."""
        agent = Agent8KParser()
        with pytest.raises(ValueError):
            await agent("invalid_state")

class TestAgent8KAnalyzer_801:
    """Test cases for Agent8KAnalyzer_801."""
    
    def test_init(self):
        """Test agent initialization."""
        agent = Agent8KAnalyzer_801()
        assert agent is not None
    
    @patch('alpha_pulse.agents.edgar.agent_8k_801_analyzer.ChatPromptTemplate')
    def test_call(self, mock_prompt, sample_state, mock_llm):
        """Test agent call method."""
        # Setup
        agent = Agent8KAnalyzer_801()
        mock_prompt.return_value.invoke.return_value = mock_llm.invoke.return_value
        
        # Execute
        result = agent(sample_state)
        
        # Verify
        assert isinstance(result, State8K)
        assert "8.01" in result.parsed_items
        item = result.parsed_items["8.01"]
        assert isinstance(item, Item8K_801)
        assert item.event_type == "Strategic Restructuring"
        assert item.sentiment == 1
        assert item.event_summary == "Company announced strategic partnership"
        assert item.key_takeaway == "Positive impact on future revenue"
        assert item.probable_price_move is True
        assert item.is_financially_material is True
        assert item.is_operational_impact is True
        assert item.is_related_to_prior is False
        assert item.is_recent_event is True
        assert item.unexpected_timing is False
        assert item.mentioned_companies == "ABC Corp"
        assert item.keywords == "partnership, AI, technology"
        assert item.strategic_signal is True
        assert item.priority_shift_detected is True
    
    def test_call_with_invalid_state(self):
        """Test agent call with invalid state."""
        agent = Agent8KAnalyzer_801()
        with pytest.raises(ValueError):
            agent("invalid_state")
    
    def test_call_with_missing_parsed_items(self):
        """Test agent call with state missing parsed_items."""
        agent = Agent8KAnalyzer_801()
        state = State8K(
            cik="0001234567",
            filing_date="2024-01-01",
            raw_text="Test text",
            items="8.01"
        )
        with pytest.raises(ValueError):
            agent(state)
    
    def test_call_with_missing_item(self):
        """Test agent call with state missing required item."""
        agent = Agent8KAnalyzer_801()
        state = State8K(
            cik="0001234567",
            filing_date="2024-01-01",
            raw_text="Test text",
            items="8.01",
            parsed_items={"8.02": Mock()}
        )
        with pytest.raises(ValueError):
            agent(state) 