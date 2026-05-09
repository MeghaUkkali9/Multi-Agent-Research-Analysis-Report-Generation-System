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