import logging
import os
from typing import Dict, Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.schema import Document

from src.settings import Settings
from src.utils.diff_parser import DiffParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGManager:
    def __init__(self):
        self.vectorstore: Optional[FAISS] = None
        self._embedding_cache: Dict[str, list] = {}

        openai_api_key = Settings.OPENAI_API_KEY

        if not openai_api_key:
            logger.warning("[RAG] OPENAI_API_KEY not found in .env")

        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small", openai_api_key=openai_api_key
        )
        logger.info("[RAG] RAG Manager initialized with OpenAI Embeddings")

    def create_from_pr_data(self, pr_data: Dict, chunk_size: int = 800) -> None:
        logger.info(f"[RAG] Creating vectorstore from PR #{pr_data.get('pr_id')}")

        files = pr_data.get("files", [])

        if not files:
            logger.warning("[RAG] No files in PR data, skipping RAG creation")
            return

        documents = []

        for file_info in files:
            file_path = file_info.get("path", "unknown")
            diff_text = file_info.get("diff", "")

            if not diff_text or diff_text.strip() == "":
                logger.debug(f"[RAG] Skipping empty diff for {file_path}")
                continue

            parsed_diff = DiffParser.parse_diff(diff_text)
            line_ranges = DiffParser.get_changed_line_ranges(diff_text)

            line_start = line_ranges[0][0] if line_ranges else None
            line_end = line_ranges[-1][1] if line_ranges else None

            doc = Document(
                page_content=diff_text,
                metadata={
                    "file": file_path,
                    "change_type": file_info.get("change_type", "unknown"),
                    "additions": file_info.get("additions", 0),
                    "deletions": file_info.get("deletions", 0),
                    "extension": (
                        file_path.split(".")[-1] if "." in file_path else "unknown"
                    ),
                    "line_start": line_start,
                    "line_end": line_end,
                    "total_chunks": parsed_diff["total_chunks"],
                },
            )
            documents.append(doc)

        logger.info(
            f"[RAG] Prepared {len(documents)} documents from {len(files)} files"
        )

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=120,
            separators=["\n@@", "\n\n", "\n", " "],
            length_function=len,
        )

        chunks = splitter.split_documents(documents)

        logger.info(f"[RAG] Split into {len(chunks)} chunks (chunk_size={chunk_size})")

        if not chunks:
            logger.warning("[RAG] No chunks created, RAG will be empty")
            return

        logger.info("[RAG] Creating embeddings and FAISS index...")

        try:
            self.vectorstore = FAISS.from_documents(
                documents=chunks, embedding=self.embeddings
            )

            logger.info(f"[RAG] ✅ Vectorstore created with {len(chunks)} chunks")

        except Exception as e:
            logger.error(f"[RAG] ❌ Error creating vectorstore: {e}")
            raise

    def _get_query_embedding(self, query: str) -> list:
        if query in self._embedding_cache:
            logger.info(f"[RAG] Cache HIT for query: '{query[:50]}...'")
            return self._embedding_cache[query]

        logger.info(f"[RAG] Cache MISS for query: '{query[:50]}...', generating embedding")
        embedding = self.embeddings.embed_query(query)
        self._embedding_cache[query] = embedding
        return embedding

    def search(
        self, query: str, k: int = 5, filter_extension: Optional[str] = None
    ) -> str:
        if self.vectorstore is None:
            logger.error(
                "[RAG] Vectorstore not created. Call create_from_pr_data first!"
            )
            return "❌ RAG não foi criado. Não é possível buscar no código."

        logger.info(f"[RAG] Searching for: '{query}' (top {k})")

        try:
            query_embedding = self._get_query_embedding(query)
            docs = self.vectorstore.similarity_search_by_vector(query_embedding, k=k * 2)

            if filter_extension:
                docs = [
                    doc
                    for doc in docs
                    if doc.metadata.get("extension") == filter_extension
                ]
                logger.info(
                    f"[RAG] Filtered by extension '{filter_extension}': {len(docs)} results"
                )

            docs = docs[:k]

            if not docs:
                return f"❌ Nenhum trecho de código encontrado para: '{query}'"

            result_parts = [f"Encontrados {len(docs)} trechos:\n"]

            for i, doc in enumerate(docs, 1):
                file_path = doc.metadata.get("file", "unknown")
                line_start = doc.metadata.get("line_start")
                line_end = doc.metadata.get("line_end")

                location = f"{file_path}"
                if line_start:
                    if line_end and line_end != line_start:
                        location += f" (lines {line_start}-{line_end})"
                    else:
                        location += f" (line {line_start})"

                result_parts.append(f"\n[{i}] {location}")
                result_parts.append(doc.page_content)

            formatted_result = "\n".join(result_parts)

            logger.info(f"[RAG] ✅ Returned {len(docs)} relevant chunks")

            return formatted_result

        except Exception as e:
            logger.error(f"[RAG] ❌ Error searching: {e}")
            return f"❌ Erro ao buscar no código: {str(e)}"

    def get_all_files_summary(self) -> str:
        if self.vectorstore is None:
            return "❌ RAG não foi criado."

        all_docs = self.vectorstore.similarity_search("", k=1000)

        files_info = {}
        for doc in all_docs:
            file_path = doc.metadata.get("file", "unknown")
            if file_path not in files_info:
                files_info[file_path] = {
                    "additions": doc.metadata.get("additions", 0),
                    "deletions": doc.metadata.get("deletions", 0),
                    "extension": doc.metadata.get("extension", "unknown"),
                }

        summary_parts = [f"📊 PR contém {len(files_info)} arquivos modificados:\n"]

        for file_path, info in sorted(files_info.items()):
            summary_parts.append(
                f"  • {file_path} ({info['extension']}) - "
                f"+{info['additions']} -{info['deletions']}"
            )

        return "\n".join(summary_parts)

    def cleanup(self):
        if self.vectorstore is not None:
            logger.info("[RAG] 🗑️ Cleaning up vectorstore")
            self.vectorstore = None
        else:
            logger.info("[RAG] No vectorstore to cleanup")

        if self._embedding_cache:
            cache_size = len(self._embedding_cache)
            logger.info(f"[RAG] 🗑️ Clearing embedding cache ({cache_size} entries)")
            self._embedding_cache.clear()
        else:
            logger.info("[RAG] No embedding cache to cleanup")
