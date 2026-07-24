from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    groq_api_key: str = ""
    groq_api_key_chat: str = ""  # optional; falls back to groq_api_key if unset
    database_url: str = "postgresql+psycopg2://aivoa:aivoa@localhost:5432/aivoa"

    # gemma2-9b-it (the model named in the assessment doc) was decommissioned by Groq;
    # llama-3.1-8b-instant is the closest still-supported equivalent (small/fast/cheap).
    extraction_model: str = "llama-3.1-8b-instant"
    chat_model: str = "llama-3.3-70b-versatile"

    max_upload_bytes: int = 10 * 1024 * 1024  # 10MB, matches reference UI
    allowed_extensions: set[str] = {".pdf", ".docx", ".txt", ".eml"}


settings = Settings()
