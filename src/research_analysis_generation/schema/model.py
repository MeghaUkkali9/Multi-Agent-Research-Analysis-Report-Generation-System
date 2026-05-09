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

class GenerateAnalystsState(TypedDict):
    topic: str  # Research topic
    max_analysts: int  # Number of analysts to generate
    human_analyst_feedback: str  # Feedback from human
    analysts: NotRequired[List[Analyst]]  # Generated analysts


class InterviewState(MessagesState):
    max_num_turns: int  # Max interview turns allowed
    context: Annotated[List[str], operator.add]  # Retrieved/search context
    analyst: Analyst  # Analyst conducting interview
    interview: str  # Full interview transcript (flattened)
    sections: List[Section]  # Sections generated from interview


class ResearchGraphState(TypedDict):
    topic: str  # Research topic
    max_analysts: int  # Number of analysts
    human_analyst_feedback: str  # Optional human feedback
    analysts: List[Analyst]  # All analysts involved

    # Aggregated sections across analysts
    sections: Annotated[List[Section], operator.add]

    # Final report components
    introduction: str
    content: str
    conclusion: str
    final_report: str