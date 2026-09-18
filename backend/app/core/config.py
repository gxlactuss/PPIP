from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Placement Prep API"
    database_url: str = "postgresql+psycopg2://postgres:121726@localhost:5432/placed_db"

    jwt_secret_key: str = "CHANGE_ME_IN_ENV"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    gemini_api_key: str = ""

    cors_origins: list[str] = ["*"]

    class Config:
        env_file = ".env"


settings = Settings()
