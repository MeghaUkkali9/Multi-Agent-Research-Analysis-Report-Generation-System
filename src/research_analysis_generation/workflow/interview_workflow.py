from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.messages import get_buffer_string

from research_analysis_generation.logger import GLOBAL_LOGGER
from research_analysis_generation.exception.custom_exception import ResearchAnalysisException
from research_analysis_generation.schema.model import InterviewState
from research_analysis_generation.prompt_lib.prompt import (
    ANALYST_ASK_QUESTIONS,
    GENERATE_SEARCH_QUERY,
    GENERATE_ANSWERS,
    WRITE_SECTION,
)

class InterviewGraphBuilder:
    def __init__(self, llm, tavily_search):
        self.llm = llm
        self.tavily_search = tavily_search
        self.memory = MemorySaver()
        self.logger = GLOBAL_LOGGER.bind(module="InterviewGraphBuilder")
    
    def generate_question(state: InterviewState):
        pass
    
    def search_web(state: InterviewState):
        pass
    
    def generate_answer(state: InterviewState):
        pass
    
    def save_transcript(state:InterviewState):
        pass
    
    def write_section(state:InterviewState):
        pass
    
    def build_graph(self):
        """
        Construct the interview workflow graph for the research analysis report generation process.
        """
        try:
            self.logger.info("Starting to build the interview workflow graph.")
            graph = StateGraph(InterviewState)
            
            graph.add_node("generate_question", self.generate_question)
            graph.add_node("search_web", self.search_web)
            graph.add_node("generate_answer", self.generate_answer)
            graph.add_node("save_transcript", self.save_transcript)
            graph.add_node("write_section", self.write_section)
            
            graph.add_edge(START, "generate_question")
            graph.add_edge("generate_question", "search_web")
            graph.add_edge("search_web", "generate_answer")
            graph.add_edge("generate_answer", "save_transcript")
            graph.add_edge("save_transcript", "write_section")
            graph.add_edge("write_section", END)
            
            graph.compile(checkpointer=self.memory)
            self.logger.info("Interview workflow graph successfully built and compiled.")
            
            return graph
        except Exception as e:
            self.logger.error(f"Error building interview workflow graph: {e}")
            raise ResearchAnalysisException("Failed to build interview workflow graph", e)