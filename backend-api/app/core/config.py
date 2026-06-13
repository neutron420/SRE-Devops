from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GEMINI_API_KEY: str = "your_gemini_api_key_here"
    DISCORD_TOKEN: str = ""
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    CHROMADB_PERSIST_DIRECTORY: str = "./vector-db/chroma_data"
    
    class Config:
        # FastAPI will look for the .env file in the project root first
        env_file = "../.env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
