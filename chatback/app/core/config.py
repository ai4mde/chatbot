from pydantic_settings import BaseSettings
from typing import Optional
import os
from .path_utils import sanitize_path_component, validate_path, ensure_path
from .version import __version__ as APP_VERSION


class Settings(BaseSettings):
    PROJECT_NAME: str = "ChatBack API"
    VERSION: str = APP_VERSION
    API_V1_STR: str = "/api/v1"

    # Database settings
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "chatbot_db"
    POSTGRES_HOST: str = "localhost"
    DATABASE_URL: Optional[str] = None
    POSTGRES_SERVER: str = "localhost"

    # Vector Database settings
    PGVECTOR_HOST: str = "localhost"
    PGVECTOR_PORT: int = 5432
    PGVECTOR_USER: str = "postgres"
    PGVECTOR_PASSWORD: str = "postgres"
    PGVECTOR_DB: str = "vector_db"
    PGVECTOR_URL: Optional[str] = None

    # Redis settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: Optional[str] = None
    REDIS_TIMEOUT: int = 5  # General operations timeout
    REDIS_SOCKET_TIMEOUT: int = 10  # Socket operations timeout
    REDIS_CONNECT_TIMEOUT: int = 5  # Connection establishment timeout
    REDIS_RETRY_ATTEMPTS: int = 3  # Number of retry attempts
    REDIS_RETRY_DELAY: int = 1  # Delay between retries in seconds
    REDIS_DATA_TTL: int = 3600 * 24 * 7  # Chat history data expiration (1 week)

    # JWT settings
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120

    # OpenAI settings
    OPENAI_API_KEY: str
    OPENAI_TIMEOUT: int = 60
    OPENAI_MAX_RETRIES: int = 3

    # Agent Smith settings
    AGENT_SMITH_MODEL: str
    AGENT_SMITH_TEMPERATURE: float
    AGENT_SMITH_NAME: str

    # Agent Jones settings
    AGENT_JONES_NAME: str
    AGENT_JONES_MODEL: str
    AGENT_JONES_TEMPERATURE: float

    # Agent Jackson settings
    AGENT_JACKSON_NAME: str
    AGENT_JACKSON_MODEL: str
    AGENT_JACKSON_TEMPERATURE: float

    # Agent Brown settings
    AGENT_BROWN_NAME: str
    AGENT_BROWN_MODEL: str
    AGENT_BROWN_TEMPERATURE: float

    # Agent White settings
    AGENT_WHITE_NAME: str
    AGENT_WHITE_MODEL: str
    AGENT_WHITE_TEMPERATURE: float

    CHATFRONT_URL: str = os.getenv("CHATFRONT_URL", "http://chatfront:3000")

    # Qdrant settings
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333

    # File system paths
    # SHARED_DATA_PATH: str = os.getenv("SHARED_DATA_PATH", "/chatback/userdata")
    # CHATBACK_DATA_PATH: str = os.getenv("CHATBACK_DATA_PATH", "/chatback/data")
    CHATBOT_DATA_PATH: str = os.getenv("CHATBOT_DATA_PATH", "/chatback/data")

    # Logging Level
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Derived paths for templates
    TEMPLATES_PATH: str = os.path.join(CHATBOT_DATA_PATH, "templates")

    STUDIO_API_URL: str = (
        "https://acc-api.ai4mde.org/api/v1"  # default value as fallback
    )

    AGENT_SUMMARY_MODEL: str = os.getenv("AGENT_SUMMARY_MODEL", "gpt-3.5-turbo-16k")

    @staticmethod
    def get_user_data_path(username: str) -> str:
        """Get the user-specific data path."""
        sanitized_username = sanitize_path_component(username)
        path = os.path.join(settings.CHATBOT_DATA_PATH, sanitized_username)

        # Validate path
        validated_path = validate_path(path, settings.CHATBOT_DATA_PATH)
        if not validated_path:
            raise ValueError(f"Invalid user data path: {path}")

        # Ensure path exists
        if not ensure_path(validated_path):
            raise OSError(f"Failed to create user data path: {validated_path}")

        return validated_path

    @staticmethod
    def get_user_srs_path(username: str) -> str:
        """Get the user-specific SRS documents path."""
        base_path = settings.get_user_data_path(username)
        path = f"{base_path}/srsdocs"

        validated_path = validate_path(path, base_path)
        if not validated_path:
            raise ValueError(f"Invalid SRS path: {path}")

        if not ensure_path(validated_path):
            raise OSError(f"Failed to create SRS path: {validated_path}")

        return validated_path

    @staticmethod
    def get_user_interviews_path(username: str) -> str:
        """Get the user-specific interviews path."""
        return os.path.join(settings.get_user_data_path(username), "interviews")

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"

    class Config:
        env_file = "config/chatback.env"  # Path relative to WORKDIR

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set up PostgreSQL URL
        self.DATABASE_URL = f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}/{self.POSTGRES_DB}"

        # Set up PGVector URL
        self.PGVECTOR_URL = f"postgresql://{self.PGVECTOR_USER}:{self.PGVECTOR_PASSWORD}@{self.PGVECTOR_HOST}:{self.PGVECTOR_PORT}/{self.PGVECTOR_DB}"

        # Set up Redis URL
        self.REDIS_URL = f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}"


settings = Settings()
