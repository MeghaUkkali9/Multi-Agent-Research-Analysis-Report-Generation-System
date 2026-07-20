from typing import Annotated, List, Optional
from typing_extensions import TypedDict, NotRequired
from langgraph.graph import MessagesState
from pydantic import Field, BaseModel
import operator

class Analyst(BaseModel):
    affiliation: str = Field(description="Primary affiliation of the analyst.")
    name: str = Field(description="Name of the analyst.")
    role: str = Field(description="Role of the analyst in the context of the topic.")
    description: str = Field(
        description="Description of the analyst's focus, concerns, and motives."
    )

    @property
    def persona(self) -> str:
        """Returns a prompt-ready persona description."""
        return (
            f"Name: {self.name}\n"
            f"Role: {self.role}\n"
            f"Affiliation: {self.affiliation}\n"
            f"Description: {self.description}\n"
        )

class Perspectives(BaseModel):
    analysts: List[Analyst] = Field(
        description="Comprehensive list of analysts with their roles and affiliations."
    )

class Section(BaseModel):
    title: str = Field(description="Title of the report section.")
    content: str = Field(description="Content of the section.")

class SearchQuery(BaseModel):
    search_query: Optional[str] = Field(
        default=None,
        description="Search query for retrieval."
    )

class SectionReview(BaseModel):
    approved: bool = Field(
        description="True if the section meets the quality bar and needs no further revision."
    )
    feedback: str = Field(
        description="Specific, actionable feedback describing what to fix. Empty if approved."
    )

class CitationCheck(BaseModel):
    all_claims_supported: bool = Field(
        description="True only if every factual claim and citation in the section is backed by the provided source context."
    )
    unsupported_claims: List[str] = Field(
        default_factory=list,
        description="Claims or citations in the section not backed by the provided context, quoted verbatim. Empty if all_claims_supported is true."
    )

class GenerateAnalystsState(TypedDict):
    topic: str  
    max_analysts: int 
    human_analyst_feedback: str  
    analysts: NotRequired[List[Analyst]]  


class InterviewState(MessagesState):
    max_num_turns: int
    context: Annotated[List[str], operator.add]
    analyst: Analyst
    interview: str
    sections: List[Section]
    section_feedback: NotRequired[str]
    section_approved: NotRequired[bool]
    revision_count: NotRequired[int]

class ResearchGraphState(TypedDict):
    topic: str  
    max_analysts: int  
    human_analyst_feedback: str  
    analysts: List[Analyst] 
    sections: Annotated[List[Section], operator.add]
    introduction: str
    content: str
    conclusion: str
    final_report: str