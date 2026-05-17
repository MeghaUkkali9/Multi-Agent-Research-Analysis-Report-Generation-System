import os
import sys
from datetime import datetime
from typing import Optional
from langgraph.types import Send
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.messages import get_buffer_string
from langchain_community.tools.tavily_search import TavilySearchResults

from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from research_analysis_generation.exception.custom_exception import ResearchAnalysisException
from research_analysis_generation.workflow.interview_workflow import InterviewGraphBuilder
from research_analysis_generation.schema.model import (
    Analyst,
    Perspectives,
    GenerateAnalystsState,
    InterviewState,
    ResearchGraphState
)
from research_analysis_generation.utils.api_key_manager import ApiKeyManager
from research_analysis_generation.logger import GLOBAL_LOGGER
from research_analysis_generation.utils.model_loader import ModelLoader

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.append(project_root)
    
class ReportGenerator:
    def __init__(self):
        self.llm = llm
        self.memory = MemorySaver()
        self.logger = GLOBAL_LOGGER.bind(module = "ReportGenerator")
        
        self.tavily_search = TavilySearchResults(api_key=ApiKeyManager().get("TAVILY_API_KEY"))
    
    def create_analyst(self):
        pass
    
    def human_feedback(self):
        pass
    
    def write_introduction(self):
        pass
    
    def write_conclusion(self):
        pass
    
    def write_report(self):
        pass
    
    def finalize_report(self):
        pass
    
    def save_report(self):
        pass
    
    def __save_as_docx(self):
        pass
    
    def __save_as_pdf(self):
        pass
    
    def initiate_all_interviews(self, state: ResearchGraphState):
        topic = state.get("topic", "Untitled Topic")
        analysts = state.get("analysts", [])

        if not analysts:
            self.logger.warning("No analysts found — skipping interviews")
            return END

        return [
            Send(
                "conduct_interview",
                {
                    "analyst": analyst,
                    "messages": [
                        HumanMessage(
                            content=f"So, let's discuss about {topic}."
                        )
                    ],
                    "max_num_turns": 2,
                    "context": [],
                    "interview": "",
                    "sections": [],
                },
            )
            for analyst in analysts
        ]
    def build_graph(self):
        """ Construct the report workflow graph for the research analysis report generation process. """
        try:
            self.logger.info("Starting to build the report workflow graph.")
            interview_graph = InterviewGraphBuilder(self.llm, self.tavily_search).build()

            graph = StateGraph(ResearchGraphState)
            
            graph.add_node("create_analyst", self.create_analyst)
            graph.add_node("human_feedback", self.human_feedback)
            graph.add_node("conduct_interview", interview_graph)
            graph.add_node("write_report", self.write_report)
            graph.add_node("write_introduction", self.write_introduction)
            graph.add_node("write_conclusion", self.write_conclusion)
            graph.add_node("finalize_report", self.finalize_report)
            
            graph.add_edge(START, "create_analyst")
            graph.add_edge("create_analyst", "human_feedback")
            graph.add_conditional_edges("human_feedback", 
                                        self.initiate_all_interviews,
                                        ["conduct_interview", END])
            graph.add_edge("conduct_interview", "write_report")
            graph.add_edge("conduct_interview", "write_introduction")
            graph.add_edge("conduct_interview", "write_conclusion")
            graph.add_edge(["write_report","write_introduction", "write_conclusion"], "finalize_report")
            graph.add_edge("finalize_report", END)
            
            report_graph = graph.compile(interrupt_before=["human_feedback"], checkpointer= self.memory)
            self.logger.info("Report workflow graph successfully built and compiled.")
            
            return report_graph
        except Exception as e:
            self.logger.error(f"Error building report workflow graph: {e}")
            raise ResearchAnalysisException("Failed to build report workflow graph", e)
    
    
if __name__ == "__main__":
    llm = ModelLoader().load_llm()
    res = llm.invoke("Hello")
    print(res.content)
    report_generator = ReportGenerator()
    
    report_generator.build_graph()
    