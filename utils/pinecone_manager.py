import os
import uuid
import logging
from pinecone import Pinecone, ServerlessSpec
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from settings import SharedSettings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class PineconeManager:
    def __init__(self, namespace: str):
        index_name = SharedSettings.PINECONE_INDEX_NAME
        openai_api_key = SharedSettings.OPENAI_API_KEY

        if not openai_api_key or not index_name:
            logger.error("Missing required environment variables")
            raise ValueError("PINECONE_API_KEY e PINECONE_INDEX_NAME must be defined at .env")

        if not namespace:
            logger.error("Empty namespace provided")
            raise ValueError("namespace cannot be empty.")

        logger.info(f"Initializing PineconeManager with namespace: {namespace}")
        self.namespace = namespace

        self.pinecone = Pinecone(api_key=SharedSettings.PINECONE_API_KEY)
        self.index_name = index_name

        if not openai_api_key:
            logger.error("OpenAI API key not provided")
            raise ValueError("OpenAI API key was not received by PineconeManager.")

        logger.info("Setting up OpenAI embeddings")
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=openai_api_key
        )

        logger.info("Setting up text splitter")
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=120,
        )

        self._create_index_if_not_exists()
        self.index = self.pinecone.Index(self.index_name)
        logger.info(f"PineconeManager initialization complete for namespace: {namespace}")

    def namespace_has_vectors(self) -> bool:
        try:
            logger.info(f"Checking if namespace '{self.namespace}' has vectors")
            stats = self.index.describe_index_stats()

            if self.namespace in stats.namespaces and stats.namespaces[self.namespace].vector_count > 0:
                logger.info(
                    f"Namespace '{self.namespace}' already contains {stats.namespaces[self.namespace].vector_count} vectors.")
                return True
            else:
                logger.info(f"Namespace '{self.namespace}' is empty or does not exist in the statistics.")
                return False
        except Exception as e:
            logger.error(f"Error checking namespace statistics '{self.namespace}': {e}")
            return False

    def _create_index_if_not_exists(self):
        logger.info(f"Checking if index '{self.index_name}' exists")
        list_of_index_objects = self.pinecone.list_indexes()
        existing_index_names = [index.name for index in list_of_index_objects]

        if self.index_name not in existing_index_names:
            logger.info(f"Creating index {self.index_name}...")
            self.pinecone.create_index(
                name=self.index_name,
                dimension=1536,
                metric='cosine',
                spec=ServerlessSpec(cloud='aws', region='us-east-1')
            )
            logger.info(f"Index {self.index_name} successfully created.")
        else:
            logger.info(f"Using existing index: {self.index_name}")

    def add_documents(self, documents: list[str]):
        if not documents:
            logger.info("No document to add.")
            return

        logger.info(f"Processing {len(documents)} documents")
        logger.info("Splitting documents in chunks...")
        all_chunks = self.text_splitter.split_text("\n\n".join(documents))

        if not all_chunks:
            logger.info("No chunk generated.")
            return

        logger.info(f"Generating embeddings for {len(all_chunks)} chunks...")
        vectors_to_upsert = []
        batch_size = 100
        for i in range(0, len(all_chunks), batch_size):
            batch = all_chunks[i:i + batch_size]
            try:
                logger.info(f"Processing batch {i // batch_size + 1}/{(len(all_chunks) - 1) // batch_size + 1}")
                embeddings_batch = self.embeddings.embed_documents(batch)
                for chunk, embedding in zip(batch, embeddings_batch):
                    vectors_to_upsert.append({
                        "id": str(uuid.uuid4()),
                        "values": embedding,
                        "metadata": {"text": chunk}
                    })
                logger.info(f"Batch {i // batch_size + 1} of embeddings successfully generated.")
            except Exception as e:
                logger.error(f"Error processing batch {i // batch_size + 1}: {e}")
                continue

        if vectors_to_upsert:
            try:
                logger.info(f"Uploading {len(vectors_to_upsert)} vectors to namespace '{self.namespace}'...")
                self.index.upsert(vectors=vectors_to_upsert, namespace=self.namespace, batch_size=100)
                logger.info("Upload to Pinecone completed successfully.")
            except Exception as e:
                logger.error(f"Error uploading to Pinecone: {e}")

    def search_documents(self, query: str, k: int = 5) -> list[str]:
        try:
            logger.info(f"Searching for: '{query}' in namespace '{self.namespace}'")
            query_embedding = self.embeddings.embed_query(query)
            results = self.index.query(
                vector=query_embedding,
                top_k=k,
                include_metadata=True,
                namespace=self.namespace
            )
            matches = [match.metadata['text'] for match in results.matches if 'text' in match.metadata]
            logger.info(f"Found {len(matches)} matches for query")
            return matches
        except Exception as e:
            logger.error(f"Error during namespace lookup '{self.namespace}': {e}")
            return []

    def get_index_stats(self):
        try:
            logger.info("Fetching index statistics")
            stats = self.index.describe_index_stats()
            logger.info(f"Index stats retrieved successfully")
            return stats
        except Exception as e:
            logger.error(f"Error when obtaining statistics of index: {e}")
            return None

    def delete_all_vectors(self) -> bool:
        try:
            logger.info(f"Starting namespace cleanup: '{self.namespace}'...")
            self.index.delete(delete_all=True, namespace=self.namespace)
            logger.info(f"Namespace '{self.namespace}' successfully cleaned.")
            return True
        except Exception as e:
            logger.error(f"Error while trying to clear namespace '{self.namespace}': {e}")
            return False