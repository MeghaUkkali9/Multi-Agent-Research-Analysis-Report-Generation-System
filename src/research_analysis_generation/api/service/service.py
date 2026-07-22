import uuid
import os
import threading
from fastapi.responses import FileResponse
from research_analysis_generation.utils.model_loader import ModelLoader
from research_analysis_generation.utils.api_key_manager import ApiKeyManager
from research_analysis_generation.workflow.workflow import ReportGenerator as AutonomousReportGenerator
from research_analysis_generation.logger import GLOBAL_LOGGER
from research_analysis_generation.exception.custom_exception import ResearchAnalysisException
from langgraph.checkpoint.memory import MemorySaver

_shared_memory = MemorySaver()

class ReportService:
    def __init__(self):
        self.llm = ModelLoader().load_llm()
        self.reporter = AutonomousReportGenerator(self.llm)
        self.reporter.memory = _shared_memory
        self.graph = self.reporter.build_graph()
        self.logger = GLOBAL_LOGGER.bind(module="ReportService")

        self.langfuse_handler = None
        if ApiKeyManager().has_langfuse():
            from langfuse.langchain import CallbackHandler
            self.langfuse_handler = CallbackHandler()
            self.logger.info("Langfuse tracing enabled")
        else:
            self.logger.info("Langfuse keys not set — tracing disabled")

    def _config(self, thread: dict) -> dict:
        """Graph run config for a thread, with Langfuse tracing attached if configured."""
        config = dict(thread)
        if self.langfuse_handler:
            config["callbacks"] = [self.langfuse_handler]
        return config

    def _flush_langfuse(self):
        """
        Langfuse batches and exports traces on a background timer. This is a
        short-lived request/response app, not a long-running batch job, so
        force a flush after each run instead of hoping the timer fires before
        the process exits or the task gets recycled.
        """
        if self.langfuse_handler:
            from langfuse import get_client
            get_client().flush()

    def start_report_generation(self, topic: str, max_analysts: int):
        """
        Kick off the pipeline. This only runs create_analyst before hitting the
        human_feedback interrupt — no report exists yet at this point, just an
        analyst team waiting for review.
        """
        try:
            thread_id = str(uuid.uuid4())
            thread = {"configurable": {"thread_id": thread_id}}
            self.logger.info("Starting report pipeline", topic=topic, thread_id=thread_id)

            last_state = {}
            for last_state in self.graph.stream({"topic": topic, "max_analysts": max_analysts}, self._config(thread), stream_mode="values"):
                pass
            self._flush_langfuse()

            return {"thread_id": thread_id, "analysts": last_state.get("analysts", [])}
        except Exception as e:
            self.logger.error("Error initiating report generation", error=str(e))
            raise ResearchAnalysisException("Failed to start report generation", e)

    def submit_feedback(self, thread_id: str, feedback: str):
        """Update human feedback in graph state."""
        try:
            thread = {"configurable": {"thread_id": thread_id}}
            self.graph.update_state(thread, {"human_analyst_feedback": feedback}, as_node="human_feedback")
            self.logger.info("Feedback updated", thread_id=thread_id)
            for _ in self.graph.stream(None, self._config(thread), stream_mode="values"):
                pass
            self._flush_langfuse()
            return {"message": "Feedback processed successfully"}
        except Exception as e:
            self.logger.error("Error updating feedback", error=str(e))
            raise ResearchAnalysisException("Failed to update feedback", e)
        
    def get_report_status(self, thread_id: str):
        """Fetch latest state or final report."""
        try:
            thread = {"configurable": {"thread_id": thread_id}}
            state = self.graph.get_state(thread)
            final_report = state.values.get("final_report")
            topic = state.values.get("topic", "AI_Report") 

            if final_report:
                # now topic-based report folder name
                file_docx = self.reporter.save_report(final_report, topic, "docx")
                file_pdf = self.reporter.save_report(final_report, topic, "pdf")
                return {
                    "status": "completed",
                    "docx_path": file_docx,
                    "pdf_path": file_pdf,
                }
            return {"status": "in_progress"}
        except Exception as e:
            self.logger.error("Error fetching report status", error=str(e))
            raise ResearchAnalysisException("Failed to fetch report status", e)

    @staticmethod
    def download_file(file_name: str):
        """Download generated report."""
        report_dir = os.path.join(os.getcwd(), "src", "generated_report")

        for root, _, files in os.walk(report_dir):
            if file_name in files:
                return FileResponse(
                    path=os.path.join(root, file_name),
                    filename=file_name,
                    media_type="application/octet-stream"
                )
        return {"error": f"File {file_name} not found"}


_report_service = None
_report_service_lock = threading.Lock()

def get_report_service() -> ReportService:
    """
    Return a process-wide shared ReportService, built once on first use.
    Avoids reloading the LLM client and rebuilding both LangGraph graphs on
    every request.
    """
    global _report_service
    if _report_service is None:
        with _report_service_lock:
            if _report_service is None:
                _report_service = ReportService()
    return _report_service