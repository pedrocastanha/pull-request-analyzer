import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    AZURE_BASE_URL = os.getenv("AZURE_BASE_URL")
    AZURE_OAUTH_TOKEN = os.getenv("AZURE_OAUTH_TOKEN")
    AZURE_API_VERSION_HEADER = os.getenv("AZURE_API_VERSION_HEADER")
    AZURE_API_VERSION = os.getenv("AZURE_API_VERSION")
    AZURE_REPOSITORY_ID = os.getenv("AZURE_REPOSITORY_ID")
    GOOGLE_GENAI_API_KEY = os.getenv("GOOGLE_GENAI_API_KEY")
