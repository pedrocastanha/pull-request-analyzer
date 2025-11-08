import logging
from pinecone import Pinecone
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from src.settings import Settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class PineconeManager:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.pinecone = Pinecone(api_key=self.settings.PINECONE_API_KEY)
        self.index = self.pinecone.Index(self.settings.PINECONE_INDEX_NAME)
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=self.settings.GEMINI_MODEL_NAME
        )
        self.namespace = self.settings.PINECONE_NAMESPACE

    def search_documents(self, query: str, k: int = 3) -> list[str]:
        try:
            logger.info(f"Searching for: '{query}' in namespace '{self.namespace}'")
            query_embedding = self.embeddings.embed_query(query)
            results = self.index.query(
                vector=query_embedding,
                top_k=k,
                include_metadata=True,
                namespace=self.namespace,
            )
            matches = [
                match.metadata["text"]
                for match in results.matches
                if "text" in match.metadata
            ]
            logger.info(f"Found {len(matches)} matches for query")
            return matches
        except Exception as e:
            logger.error(f"Error during namespace lookup '{self.namespace}': {e}")
            raise
