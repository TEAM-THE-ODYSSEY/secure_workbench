from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Settings:
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    data_dir: str = os.getenv("AGENT_DATA_DIR", "./data")
    upload_dir: str = os.getenv("AGENT_UPLOAD_DIR", "./data/uploads")
    db_path: str = os.getenv("AGENT_DB_PATH", "./data/agentic_engine.db")
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    timeout: int = int(os.getenv("LLM_TIMEOUT", "180"))
    max_history: int = int(os.getenv("MAX_HISTORY_MESSAGES", "20"))
    max_context_chars: int = int(os.getenv("MAX_CONTEXT_CHARS", "30000"))
