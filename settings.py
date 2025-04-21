# forest_app/config/settings.py

import os

class Settings:
    # Ollama / LLM settings you already have…
    llm_api_endpoint: str = os.getenv("LLM_API_ENDPOINT", "http://localhost:11434/api/generate")
    llm_api_key: str      = os.getenv("LLM_API_KEY", "")
    llm_model_name: str   = os.getenv("LLM_MODEL_NAME", "mistral")

    # Database URL used by SQLAlchemy
    db_connection_string: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./forest.db"     # or whatever default makes sense for you
    )

settings = Settings()