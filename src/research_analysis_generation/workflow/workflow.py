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
from research_analysis_generation.prompt_lib.prompt import (
    CREATE_ANALYSTS_PROMPT,
    WRITE_INTRODUCTION_PROMPT,
    WRITE_CONCLUSION_PROMPT,
    WRITE_REPORT_PROMPT,
    FINALIZE_REPORT_PROMPT,
    REPORT_WRITER_INSTRUCTIONS,
    INTRO_CONCLUSION_INSTRUCTIONS
)

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.append(project_root)
    
class ReportGenerator:
    def __init__(self):
        self.llm = llm
        self.memory = MemorySaver()
        self.logger = GLOBAL_LOGGER.bind(module = "ReportGenerator")
        
        self.tavily_search = TavilySearchResults(api_key=ApiKeyManager().get("TAVILY_API_KEY"))
    
    def create_analyst(self, state: GenerateAnalystsState):
        topic = state["topic"]
        max_analysts = state["max_analysts"]
        human_analyst_feedback = state.get("human_analyst_feedback", "")
        try:
            self.logger.info(f"Creating analysts for topic: {topic} with max analysts: {max_analysts}")
            
            structured_llm = self.llm.with_structured_output(Perspectives)
            system_message = CREATE_ANALYSTS_PROMPT.render(
                topic= topic,
                human_analyst_feedback= human_analyst_feedback,
                max_analysts= max_analysts
            )
            analysts = structured_llm.invoke([
                SystemMessage(content= system_message),
                HumanMessage(content= "create a list of analysts")
            ])
            return {
                "analysts": analysts.analysts
                }
        except Exception as e:
            self.logger.error(f"Error creating analysts: {e}")
            raise ResearchAnalysisException("Failed to create analysts", e)
        
    def human_feedback(self):
        """This node is a placeholder for human feedback. It does not perform any operations itself, but serves as an interruption point in the graph where human feedback can be collected and added to the state before proceeding with the report generation process.
        """
        try:
            self.logger.info("Reached human feedback node. Awaiting human feedback before proceeding.")
        except Exception as e:
            self.logger.error(f"Error in human feedback node: {e}")
            raise ResearchAnalysisException("Failed at human feedback node", e)
    
    def write_introduction(self, state: ResearchGraphState):
        """
        Writes the introduction section of the report. 
        This is a placeholder function that can be expanded in the future to generate an introduction based on the topic and sections of the report. Currently, it does not perform any operations.
        """
        try:
            sections = state.get("sections", [])
            topic = state.get("topic", [])
            formatted_sections = "\n\n".join([f"{s}" for s in sections])
            
            self.logger.info(f"Writing introduction for topic: {topic} with sections: {sections}")  
            
            system_prompt = INTRO_CONCLUSION_INSTRUCTIONS.render(
                topic=topic,
                formatted_sections= formatted_sections)
            
            introduction = self.llm.invoke([
                SystemMessage(content= system_prompt),
                HumanMessage(content="Write the introduction section for the report based on the provided sections.")])
            
            self.logger.info("Introduction successfully written.")
            return {"introduction": introduction.content}
        except Exception as e:
            self.logger.error(f"Error writing introduction: {e}")
            raise ResearchAnalysisException("Failed to write introduction", e)
    
    def write_conclusion(self, state: ResearchGraphState):
        """ Writes the conclusion section of the report."""
        try:
            sections = state["sections"]
            topic = state["topic"]
            formatted_sections = "\n\n".join([f"{s}" for s in sections])
            
            self.logger.info(f"Writing conclusion for topic: {topic} with sections: {sections}")
            
            system_prompt = INTRO_CONCLUSION_INSTRUCTIONS.render(
                topic=topic,
                formatted_sections= formatted_sections)
            
            conclustion = self.llm.invoke([
                SystemMessage(content= system_prompt),
                HumanMessage(content="Write the conclusion section for the report based on the provided sections.")])       
            
            self.logger.info("Conclusion successfully written.")
            return {"conclusion": conclustion.content}
        except Exception as e:
            self.logger.error(f"Error writing conclusion: {e}")
            raise ResearchAnalysisException("Failed to write conclusion", e)
    
    def write_report(self, state: ResearchGraphState):
        sections = state.get("sections", [])
        topic = state.get("topic", "")
        
        try:
            if not sections:
                sections = ["No sections available."]
                self.logger.warning("No sections found in state for report writing.")       
            self.logger.info(f"Writing report for topic: {topic} with sections: {sections}")
            
            system_prompt = REPORT_WRITER_INSTRUCTIONS.render(topic=topic)
            self.logger.debug(f"System prompt for report writing: {system_prompt}")
            
            report = self.llm.invoke([
                SystemMessage(content= system_prompt),
                HumanMessage(content="\n\n".join(sections))
            ])
            self.logger.info("Report successfully written.")
            return {"report": report.content}
        
        except Exception as e:
            self.logger.error(f"Error writing report: {e}")
            raise ResearchAnalysisException("Failed to write report", e)
    
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
    