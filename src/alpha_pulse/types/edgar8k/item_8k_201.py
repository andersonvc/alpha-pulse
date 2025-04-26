"""Item 2.01 type for 8-K filings."""

from typing import Literal
from pydantic import Field
from alpha_pulse.types.edgar8k.base_item_8k import BaseItem8K

# transaction types for Item 2.01
TransactionType= Literal[
    "Acquisition", "Disposition", "Merger", "Divestiture",
    "Asset Purchase", "Asset Sale", "Spin-Off", "Carve-Out",
    "Business Combination", "Other"
]

# consideration types for Item 2.01
ConsiderationType= Literal[
    "Cash", "Stock", "Debt Assumption", "Earnout", "Mixed", "Other"
]

class Item8K_201(BaseItem8K):
    """Represents an analysis of an 8-K Item 2.01 filing."""
    transaction_type: TransactionType = Field(
        ...,
        description="The type of transaction described in the 8-K item"
    )
    consideration_type: ConsiderationType = Field(
        ...,
        description="The type of consideration described in the 8-K item"
    )
    counterparties: str = Field(
        ...,
        description="The counterparties involved in the transaction"
    )
    deal_value_usd: float = Field(
        ...,
        description="The approximate value of the transaction in USD"
    )
    is_core_asset: bool = Field(
        ...,
        description="Whether the asset involved is core to the company's operations"
    )
    is_financially_material: bool = Field(
        ...,
        description="Whether the transaction is financially material"
    )
    is_operational_impact: bool = Field(
        ...,
        description="Whether the transaction has an operational impact"
    )
    strategic_rationale: str = Field(
        ...,
        description="The strategic rationale for the transaction"
    )
    sentiment: int = Field(
        ...,
        description="The sentiment of the transaction"
    )
    probable_price_move: bool = Field(
        ...,
        description="Whether the price of the company is likely to move"
    )
    price_move_reason: str = Field(
        ...,
        description="The reason for the probable price move"
    )
    is_related_to_prior: bool = Field(
        ...,
        description="Whether the transaction is related to a prior event"
    )
    mentioned_companies: str = Field(
        ...,
        description="The companies mentioned in the transaction"
    )
    mentioned_tickers: str = Field(
        ...,
        description="The tickers mentioned in the transaction"
    )
    keywords: str = Field(
        ...,
        description="The keywords in the transaction"
    )
    strategic_signal: bool = Field(
        ...,
        description="Whether the transaction is a strategic signal"
    )
    priority_shift_detected: bool = Field(
        ...,
        description="Whether the transaction is a priority shift"
    )