from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GEMINI_API_KEY: str = "your_gemini_api_key_here"
    DISCORD_TOKEN: str = ""
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    CHROMADB_PERSIST_DIRECTORY: str = "./vector-db/chroma_data"
    MOCK_MODE: bool = True
    K8S_NAMESPACE: str = "default"
    
    # Customizable PromQL queries
    PROM_QUERY_CPU: str = 'sum(rate(container_cpu_usage_seconds_total{container!="", pod=~"{service_name}.*"}[5m])) by (pod)'
    PROM_QUERY_MEMORY: str = 'sum(container_memory_working_set_bytes{container!="", pod=~"{service_name}.*"}) / 1024 / 1024'
    PROM_QUERY_MEMORY_LIMIT: str = 'sum(container_spec_memory_limit_bytes{container!="", pod=~"{service_name}.*"}) / 1024 / 1024'
    PROM_QUERY_LATENCY: str = 'sum(rate(http_request_duration_seconds_sum{pod=~"{service_name}.*"}[5m])) / sum(rate(http_request_duration_seconds_count{pod=~"{service_name}.*"}[5m])) * 1000'
    PROM_QUERY_ERROR_RATE: str = 'sum(rate(http_requests_failed_total{pod=~"{service_name}.*"}[5m])) / sum(rate(http_requests_total{pod=~"{service_name}.*"}[5m])) * 100'

    class Config:
        # FastAPI will look for the .env file in the project root first
        env_file = "../.env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
