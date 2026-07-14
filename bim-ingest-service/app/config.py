from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_key: str = Field(default="change-me", alias="BIM_SERVICE_API_KEY")
    neo4j_uri: str = Field(default="bolt://neo4j:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="bim_neo4j_password", alias="NEO4J_PASSWORD")
    lightrag_base_url: str = Field(default="", alias="LIGHTRAG_BASE_URL")
    lightrag_api_key: str = Field(default="", alias="LIGHTRAG_API_KEY")
    lightrag_mode: str = Field(default="adapter", alias="LIGHTRAG_MODE")
    workspace_prefix: str = Field(default="/home/node/.openclaw/workspace", alias="BIM_OPENCLAW_WORKSPACE_PREFIX")
    workspace_mount: str = Field(default="/workspace", alias="BIM_WORKSPACE_MOUNT")


@lru_cache
def get_settings() -> Settings:
    return Settings()
