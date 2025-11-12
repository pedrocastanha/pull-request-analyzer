import logging
import os
import tempfile
import fitz
from docx import Document
from fastapi import UploadFile, HTTPException

logging.basicConfig(level=logging.INFO)


class DocumentProcessor:
    def __init__(self):
        logging.info("DocumentProcessor initialized")

    def _extract_text_from_pdf(self, file_path: str) -> str:
        try:
            logging.info(f"Extracting text from PDF: {os.path.basename(file_path)}")
            text = ""
            with fitz.open(file_path) as pdf_document:
                for page_num, page in enumerate(pdf_document):
                    page_text = page.get_text()
                    text += page_text
                    logging.debug(
                        f"Extracted {len(page_text)} characters from page {page_num + 1}"
                    )
            logging.info(f"Successfully extracted {len(text)} characters from PDF")
            return text
        except Exception as e:
            logging.error(f"Error extracting text from PDF: {e}")
            raise

    def _extract_text_from_docx(self, file_path: str) -> str:
        try:
            logging.info(f"Extracting text from DOCX: {os.path.basename(file_path)}")
            doc = Document(file_path)
            text = ""
            for para_num, paragraph in enumerate(doc.paragraphs):
                if paragraph.text:
                    text += paragraph.text + "\n"
                    logging.debug(f"Extracted paragraph {para_num + 1}")
            logging.info(f"Successfully extracted {len(text)} characters from DOCX")
            return text
        except Exception as e:
            logging.error(f"Error extracting text from DOCX: {e}")
            raise

    def validate_file_type(self, filename: str) -> str:
        if not filename:
            logging.error("No filename provided")
            raise

        extension = filename.lower().split(".")[-1]
        logging.info(f"Validating file type: {extension}")

        if extension not in ["pdf", "docx"]:
            logging.error(f"Unsupported file type: {extension}")
            raise
        return extension

    async def extract_text_from_file(self, file: UploadFile) -> str:
        try:
            logging.info(f"Processing document: {file.filename}")

            file_type = self.validate_file_type(file.filename)

            logging.info("Saving file to temporary location")
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=f".{file_type}"
            ) as temp_file:
                content = await file.read()
                temp_file.write(content)
                temp_file_path = temp_file.name
                logging.info(f"Temporary file created at: {temp_file_path}")
            try:
                if file_type == "pdf":
                    text = self._extract_text_from_pdf(temp_file_path)
                else:
                    text = self._extract_text_from_docx(temp_file_path)

                if not text.strip():
                    logging.error("Document contains no extractable text")
                    raise HTTPException(
                        status_code=400, detail="Documento não contém texto extraível"
                    )

                logging.info(f"Successfully extracted {len(text)} characters of text")
                return text

            finally:
                if os.path.exists(temp_file_path):
                    logging.info(f"Removing temporary file: {temp_file_path}")
                    os.unlink(temp_file_path)
        except:
            raise
