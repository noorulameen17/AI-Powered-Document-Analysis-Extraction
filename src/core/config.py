from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()


class Settings(BaseModel):
    API_KEY: str = os.getenv("API_KEY", "")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    SUMMARIZATION_MODEL: str = os.getenv(
        "SUMMARIZATION_MODEL", "sshleifer/distilbart-cnn-12-6"
    )
    SENTIMENT_MODEL: str = os.getenv(
        "SENTIMENT_MODEL", "distilbert-base-uncased-finetuned-sst-2-english"
    )
    SPACY_MODEL: str = os.getenv("SPACY_MODEL", "en_core_web_sm")

    TESSERACT_CMD: str = os.getenv("TESSERACT_CMD", "")

    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "")


settings = Settings()
