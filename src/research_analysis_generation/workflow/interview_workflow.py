from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.messages import get_buffer_string

from research_analysis_generation.logger import GLOBAL_LOGGER
from research_analysis_generation.exception.custom_exception import ResearchAnalysisException
from research_analysis_generation.schema.model import InterviewState, SearchQuery
from research_analysis_generation.prompt_lib.prompt import (
    ANALYST_ASK_QUESTIONS,
    GENERATE_SEARCH_QUERY,
    GENERATE_ANSWERS,
    WRITE_SECTION,
)

class InterviewGraphBuilder:
    """
    A class responsible for constructing and managing the Interview Graph workflow.
    Handles the process of:
        1. Analyst generating questions.
        2. Performing relevant web search.
        3. Expert generating answers.
        4. Saving the interview transcript.
        5. Writing a summarized report section.
    """
    def __init__(self, llm, tavily_search):
        """
        Initialize the InterviewGraphBuilder with the LLM model and Tavily search tool.
        """
        self.llm = llm
        self.tavily_search = tavily_search
        self.memory = MemorySaver()
        self.logger = GLOBAL_LOGGER.bind(module="InterviewGraphBuilder")
    
    def generate_question(self, state: InterviewState):
        """
        Generate a question for the expert based on the current interview state and goals.
        """
        try:
            analyst = state["analyst"]
            messages = state["messages"]
            
            self.logger.info("Generating question for expert", analyst=analyst.name)
            system_prompt = ANALYST_ASK_QUESTIONS.render(goals=analyst.persona)
            
            question = self.llm.invoke([
                SystemMessage(content=system_prompt) + messages
            ])
           
            self.logger.info("Generated question", question=question.content[:200])
            return {"messages": [question]}
        except Exception as e:  
            self.logger.error(f"Error generating question: {e}")
            raise ResearchAnalysisException("Failed to generate question", e)
    
    def search_web(self, state: InterviewState):
        """
        Generate a structured search query and perform Tavily web search.
        """
        try:
            self.logger.info("Generating search query from conversation")
            
            structured_llm = self.llm.with_structured_output(SearchQuery)
            search_prompt = GENERATE_SEARCH_QUERY.render()
            
            search_query = structured_llm.invoke([
                SystemMessage(content=search_prompt) + state["messages"]
            ])
            
            self.logger.info("Generated search query", query=search_query.query)
            search_results = self.tavily_search.run(search_query.query) 
            self.logger.info("Retrieved search results", num_results=len(search_results))
            
            if not search_results:
                self.logger.warning("No search results found for query", query=search_query.query)
                return {"context": ["No search results found"]}
            
            formatted = "\n\n---\n\n".join(
                [
                    f'<Document href="{doc.get("url", "#")}"/>\n{doc.get("content", "")}\n</Document>'
                    for doc in search_results
                ]
            )
            
            self.logger.info("Formatted search results for context", formatted_length=len(formatted))
            return {"context": [formatted]}
        except Exception as e:  
            self.logger.error(f"Error during web search: {e}")
            raise ResearchAnalysisException("Failed during web search", e)
    
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