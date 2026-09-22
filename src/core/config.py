import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # TigerGraph connection
    tg_host: str = Field(default="http://127.0.0.1", alias="TG_HOST")
    tg_graph: str = Field(default="FraudGraph", alias="TG_GRAPH")
    tg_username: str = Field(default="tigergraph", alias="TG_USERNAME")
    tg_password: str = Field(default="tigergraph", alias="TG_PASSWORD")
    tg_secret: str = Field(default="", alias="TG_SECRET")
    tg_api_token: str = Field(default="", alias="TG_API_TOKEN")

    # Paths
    base_dir: Path = Path(__file__).resolve().parent.parent.parent
    data_dir: Path = Field(default=Path("HHGOA_IEEE"), alias="DATA_DIR")
    processed_data_dir: Path = Field(default=Path("data/processed"), alias="PROCESSED_DATA_DIR")
    sample_data_dir: Path = Field(default=Path("data/sample"), alias="SAMPLE_DATA_DIR")

    # LLM Settings
    llm_provider: str = Field(default="gemini", alias="LLM_PROVIDER")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")

    # Server Settings
    port: int = Field(default=8000, alias="PORT")
    host: str = Field(default="0.0.0.0", alias="HOST")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
