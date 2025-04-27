from pydantic import BaseModel, Field
from alpha_pulse.types.dbtables.parsed_8k_text import Parsed8KText
from typing import Optional, List
from datetime import date
# --- Pydantic Item 502 Models --- #
class RoleChange(BaseModel):
    name: str = Field(..., description="Full name of person mentioned")
    role: Optional[str] = Field(default="", description="Title of role held")
    effective_date: Optional[str] = Field(default="", description="Date change is effective")
    
    def to_db_dict(self, sourced_input: Parsed8KText) -> dict:
        return {
            "cik": sourced_input.cik,
            "filing_date": sourced_input.filing_date,
            "name": self.name,
            "role": self.role,
            "effective_date": self.effective_date,
        }

class Item502Summary(BaseModel):
    category: str = Field(..., description="Category for this document")
    appointment: List[RoleChange] = Field(default_factory=list, description="List of appointments")
    removal: List[RoleChange] = Field(default_factory=list, description="List of removals")
    
    def to_db_dict(self, sourced_input: Parsed8KText) -> dict:
        return {
            "category": self.category,
            "filing_date": sourced_input.filing_date,
            "cik": sourced_input.cik,
            "base_url": sourced_input.base_url,
            "item_number": sourced_input.item_number,
            "ts": sourced_input.ts,
        }