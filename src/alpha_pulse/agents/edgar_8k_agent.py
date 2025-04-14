"""Agent for analyzing SEC EDGAR 8-K filings."""

from typing import Dict, List, Optional, TypedDict
import logging

from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

from alpha_pulse.tools.edgar import parse_latest_8k_filing_tool
from alpha_pulse.types.analysis import Edgar8kAnalysis, Edgar8kAnalysisResponse
from alpha_pulse.types.state import Edgar8kState


class Edgar8kAgent:
    """Agent for analyzing SEC EDGAR 8-K filings.
    
    This agent uses OpenAI's function calling to analyze 8-K filings and provide
    insights about the company's recent developments.
    """
    
    def __init__(self, model_name: str = "gpt-4-turbo-preview") -> None:
        """Initialize the Edgar8kAgent.
        
        Args:
            model_name: Name of the OpenAI model to use
        """
        self.model = ChatOpenAI(model=model_name, temperature=0)
        
        # Initialize tools
        self.tools = [parse_latest_8k_filing_tool]
        
        # Create the prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert financial analyst specializing in SEC filings analysis.
            Your task is to analyze 8-K filings and provide clear, concise insights about the company's recent developments.
            
            When analyzing a filing:
            1. Focus on the most significant items and their implications
            2. Explain the impact on the company and its stakeholders
            3. Highlight any potential risks or opportunities
            4. Provide context about the company's industry and market position
            
            Be professional and objective in your analysis."""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # Create the agent
        self.agent = create_openai_functions_agent(
            llm=self.model,
            tools=self.tools,
            prompt=self.prompt
        )
        
        # Create the agent executor
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True
        )

    async def __call__(self, state: Edgar8kState) -> Edgar8kState:
        """Process the current state and return the next state.
        
        Args:
            state: Current state containing the ticker and any previous analysis
            
        Returns:
            Edgar8kState: Updated state with the analysis results
        """
        # Get the ticker from the state
        ticker = state["ticker"]
        
        # Create the input message
        input_message = f"Analyze the latest 8-K filing for {ticker} and provide insights about the company's recent developments."
        
        try:
            # Run the agent
            result = await self.agent_executor.ainvoke({
                "input": input_message,
                "chat_history": []
            })
            
            # Get the raw filing data
            raw_filing = await parse_latest_8k_filing_tool(ticker)
            
            # Create the analysis response
            analysis = Edgar8kAnalysis(
                ticker=ticker,
                analysis=result["output"],
                raw_filing=raw_filing,
                filing_date=state.get("filing_date", "")
            )
            
            # Update the state
            state["analysis"] = analysis
            state["raw_filing"] = raw_filing
            
        except Exception as e:
            logging.error(f"Error analyzing 8-K filing for {ticker}: {str(e)}")
            raise
        
        return state