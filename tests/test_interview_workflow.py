"""
Tests for the routing logic inside the interview graph — route_messages,
combine_reviews, and route_review. These are pure functions of state (no LLM
calls), so they're built with llm=None / tavily_search=None.
"""

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END

from research_analysis_generation.workflow.interview_workflow import InterviewGraphBuilder


@pytest.fixture
def builder():
    return InterviewGraphBuilder(llm=None, tavily_search=None)


def make_turns(num_turns, last_says_thanks=False):
    """Build a messages list with `num_turns` analyst/expert exchanges."""
    messages = [HumanMessage(content="Let's discuss the topic.")]
    for i in range(num_turns):
        is_last = i == num_turns - 1
        analyst = AIMessage(
            content="Thank you so much for your help!" if (is_last and last_says_thanks) else f"Question {i}"
        )
        analyst.name = "analyst"
        expert = AIMessage(content=f"Answer {i}")
        expert.name = "expert"
        messages += [analyst, expert]
    return messages


class TestRouteMessages:
    def test_stops_when_max_turns_reached(self, builder):
        state = {"messages": make_turns(2), "max_num_turns": 2}
        assert builder.route_messages(state) == "save_transcript"

    def test_continues_when_turns_remain(self, builder):
        state = {"messages": make_turns(1), "max_num_turns": 3}
        assert builder.route_messages(state) == "generate_question"

    def test_stops_when_analyst_says_thanks_early(self, builder):
        state = {"messages": make_turns(1, last_says_thanks=True), "max_num_turns": 5}
        assert builder.route_messages(state) == "save_transcript"


class TestRouteReview:
    def test_approved_section_ends(self, builder):
        state = {"section_approved": True, "revision_count": 1}
        assert builder.route_review(state) == END

    def test_rejected_under_cap_goes_back_to_writer(self, builder):
        state = {"section_approved": False, "revision_count": 1}
        assert builder.route_review(state) == "write_section"

    def test_cap_reached_ends_even_if_still_rejected(self, builder):
        state = {"section_approved": False, "revision_count": builder.MAX_SECTION_REVISIONS}
        assert builder.route_review(state) == END


class TestCombineReviews:
    def test_both_critics_approve(self, builder):
        state = {"section_approved": True, "citations_supported": True, "revision_count": 0}
        result = builder.combine_reviews(state)
        assert result["section_approved"] is True
        assert result["section_feedback"] == ""
        assert result["revision_count"] == 1

    def test_editor_rejects_but_fact_checker_approves(self, builder):
        state = {
            "section_approved": False,
            "section_feedback": "too generic",
            "citations_supported": True,
            "revision_count": 0,
        }
        result = builder.combine_reviews(state)
        assert result["section_approved"] is False
        assert "too generic" in result["section_feedback"]
        assert "Fact-checker" not in result["section_feedback"]

    def test_fact_checker_rejects_but_editor_approves(self, builder):
        state = {
            "section_approved": True,
            "citation_feedback": "unsupported claim about revenue",
            "citations_supported": False,
            "revision_count": 0,
        }
        result = builder.combine_reviews(state)
        assert result["section_approved"] is False
        assert "unsupported claim about revenue" in result["section_feedback"]

    def test_both_critics_reject_merges_both_feedbacks(self, builder):
        state = {
            "section_approved": False,
            "section_feedback": "too generic",
            "citations_supported": False,
            "citation_feedback": "made up a statistic",
            "revision_count": 0,
        }
        result = builder.combine_reviews(state)
        assert result["section_approved"] is False
        assert "too generic" in result["section_feedback"]
        assert "made up a statistic" in result["section_feedback"]


def test_graph_builds_and_compiles(builder):
    graph = builder.build_graph()
    assert graph is not None
