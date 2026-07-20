from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.messages import get_buffer_string

from research_analysis_generation.logger import GLOBAL_LOGGER
from research_analysis_generation.exception.custom_exception import ResearchAnalysisException
from research_analysis_generation.schema.model import InterviewState, SearchQuery, Section, SectionReview
from research_analysis_generation.prompt_lib.prompt import (
    ANALYST_ASK_QUESTIONS,
    GENERATE_SEARCH_QUERY,
    GENERATE_ANSWERS,
    WRITE_SECTION,
    REVIEW_SECTION,
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
        6. An editor agent reviewing the section and requesting revisions
           until it's approved or the revision cap is reached.
    """

    MAX_SECTION_REVISIONS = 2

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

            system_prompt = ANALYST_ASK_QUESTIONS.render(
                goals=analyst.persona
            )

            question = self.llm.invoke(
                [SystemMessage(content=system_prompt)] + messages
            )
            question.name = "analyst"

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

            search_query = structured_llm.invoke(
                [SystemMessage(content=search_prompt)] + state["messages"]
            )

            self.logger.info("Generated search query",query=search_query.search_query)

            search_results = self.tavily_search.run(
                search_query.search_query
            )

            self.logger.info("Retrieved search results", num_results=len(search_results))

            if not search_results:
                self.logger.warning("No search results found for query", query=search_query.search_query)

                return {
                    "context": ["No search results found"]
                }

            formatted = "\n\n---\n\n".join(
                [
                    f'<Document href="{doc.get("url", "#")}"/>\n'
                    f'{doc.get("content", "")}\n'
                    f'</Document>'
                    for doc in search_results
                ]
            )

            self.logger.info("Formatted search results for context", formatted_length=len(formatted))

            return {"context": [formatted]}

        except Exception as e:
            self.logger.error(f"Error during web search: {e}")
            raise ResearchAnalysisException("Failed during web search", e)
            
    def generate_answer(self, state: InterviewState):
        """
        Generate an answer from the expert based on the question and retrieved context.
        """
        try:
            analyst = state["analyst"]
            messages = state["messages"]
            context = state.get("context", ["No context available"])
            
            self.logger.info("Generating answer for expert", analyst=analyst.name)
            system_prompt = GENERATE_ANSWERS.render(goals=analyst.persona, context = context)
            
            answer = self.llm.invoke(
                [SystemMessage(content=system_prompt)] + messages
            )
            
            answer.name = "expert"
            self.logger.info("Generated answer", answer=answer.content[:200])
            
            return {"messages": [answer]}
        except Exception as e:
            self.logger.error(f"Error generating answer: {e}")
            raise ResearchAnalysisException("Failed to generate answer", e)
    
    def route_messages(self, state: InterviewState):
        """
        Decide whether the analyst should keep questioning the expert or wrap up the
        interview, based on the configured turn limit and whether the analyst has
        signaled they're satisfied.
        """
        messages = state["messages"]
        max_num_turns = state.get("max_num_turns", 2)

        num_responses = len(
            [m for m in messages if isinstance(m, AIMessage) and m.name == "expert"]
        )

        if num_responses >= max_num_turns:
            self.logger.info("Max interview turns reached", num_responses=num_responses)
            return "save_transcript"

        last_question = messages[-2]
        if "Thank you so much for your help" in last_question.content:
            self.logger.info("Analyst signaled end of interview")
            return "save_transcript"

        return "generate_question"

    def save_transcript(self, state:InterviewState):
        """
        Save the current interview transcript to memory for future reference and context.
        """
        try:
            messages = state["messages"]
            interview_transcript = get_buffer_string(messages)
            
            self.logger.info("Saving interview transcript to memory", transcript_length=len(interview_transcript))
            
            return {"interview": interview_transcript}
        
        except Exception as e:
            self.logger.error(f"Error saving transcript: {e}")
            raise ResearchAnalysisException("Failed to save transcript", e) 
        
    def write_section(self, state: InterviewState):
        """
        Write a summarized report section based on the interview transcript and goals.
        On a revision pass (section_feedback is set), rewrite the previous draft
        to address the editor's feedback rather than starting from scratch.
        """
        try:
            context = state.get(
                "context",
                ["No context available"]
            )

            analyst = state["analyst"]
            feedback = state.get("section_feedback")
            previous_sections = state.get("sections", [])

            self.logger.info(
                "Writing report section based on interview and context",
                analyst=analyst.name,
                is_revision=bool(feedback),
            )

            system_prompt = WRITE_SECTION.render(
                goals=analyst.description,
                feedback=feedback,
            )

            if feedback and previous_sections:
                human_content = (
                    f"Original source context:\n{chr(10).join(context)}\n\n"
                    f"Your previous draft:\n{previous_sections[-1].content}\n\n"
                    f"Editor feedback to address:\n{feedback}"
                )
            else:
                human_content = "\n".join(context)

            section = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_content)
            ])

            self.logger.info("Generated report section", section=section.content[:200])

            return {
                "sections": [
                    Section(
                        title=analyst.role,
                        content=section.content
                    )
                ]
            }

        except Exception as e:
            self.logger.error(f"Error writing report section: {e}")
            raise ResearchAnalysisException("Failed to write report section", e)

    def review_section(self, state: InterviewState):
        """
        Editor agent: critiques the latest section draft and either approves it
        or returns specific feedback for the writer to address on the next pass.
        """
        try:
            analyst = state["analyst"]
            section = state["sections"][-1]
            revision_count = state.get("revision_count", 0)

            self.logger.info(
                "Reviewing report section",
                analyst=analyst.name,
                attempt=revision_count + 1,
            )

            structured_llm = self.llm.with_structured_output(SectionReview)
            review_prompt = REVIEW_SECTION.render(
                goals=analyst.description,
                section=section.content,
            )

            review = structured_llm.invoke([SystemMessage(content=review_prompt)])

            self.logger.info(
                "Section review complete",
                approved=review.approved,
                feedback=review.feedback[:200],
            )

            return {
                "section_feedback": review.feedback,
                "section_approved": review.approved,
                "revision_count": revision_count + 1,
            }

        except Exception as e:
            self.logger.error(f"Error reviewing report section: {e}")
            raise ResearchAnalysisException("Failed to review report section", e)

    def route_review(self, state: InterviewState):
        """
        Loop back to the writer if the editor rejected the section and the
        revision cap hasn't been hit yet; otherwise the section is final.
        """
        if state.get("section_approved") or state.get("revision_count", 0) >= self.MAX_SECTION_REVISIONS:
            return END
        return "write_section"

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
            graph.add_node("review_section", self.review_section)

            graph.add_edge(START, "generate_question")
            graph.add_edge("generate_question", "search_web")
            graph.add_edge("search_web", "generate_answer")
            graph.add_conditional_edges(
                "generate_answer",
                self.route_messages,
                ["generate_question", "save_transcript"],
            )
            graph.add_edge("save_transcript", "write_section")
            graph.add_edge("write_section", "review_section")
            graph.add_conditional_edges(
                "review_section",
                self.route_review,
                ["write_section", END],
            )
            
            compiled_graaph = graph.compile(checkpointer=self.memory)
            self.logger.info("Interview workflow graph successfully built and compiled.")
            
            return compiled_graaph
        except Exception as e:
            self.logger.error(f"Error building interview workflow graph: {e}")
            raise ResearchAnalysisException("Failed to build interview workflow graph", e)