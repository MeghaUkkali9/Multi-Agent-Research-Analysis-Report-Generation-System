from research_analysis_generation.logger import GLOBAL_LOGGER as log
from dotenv import load_dotenv
import os 

class ApiKeyManager:
    """
    Loads and manages all environment-based API keys.
    """

    def __init__(self):
        load_dotenv()

        self.api_keys = {
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            "GROQ_API_KEY": os.getenv("GROQ_API_KEY"),
            "TAVILY_API_KEY": os.getenv("TAVILY_API_KEY"),
            "LANGCHAIN_API_KEY": os.getenv("LANGCHAIN_API_KEY"),
        }

        log.info("Initializing ApiKeyManager")

        # Log loaded key statuses without exposing secrets
        for key, val in self.api_keys.items():
            if val:
                log.info(f"{key} loaded successfully from environment")
            else:
                log.warning(f"{key} is missing in environment variables")

        self._configure_tracing()

    def _configure_tracing(self):
        """
        Enable LangSmith tracing for every LangChain/LangGraph call in this process
        when a LangSmith API key is available. LangChain reads these as plain env
        vars, so setting them here (once, at startup) is enough to trace every
        agent's calls automatically — no per-call instrumentation needed.
        """
        langsmith_key = self.api_keys.get("LANGCHAIN_API_KEY")
        if not langsmith_key:
            log.info("LANGCHAIN_API_KEY not set — LangSmith tracing disabled")
            return

        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = langsmith_key
        os.environ.setdefault("LANGCHAIN_PROJECT", "research-analysis-generation")
        log.info("LangSmith tracing enabled", project=os.environ["LANGCHAIN_PROJECT"])

    def get(self, key: str):
        """
        Retrieve a specific API key.

        Args:
            key (str): Name of the API key.

        Returns:
            str | None: API key value if found.
        """
        return self.api_keys.get(key)