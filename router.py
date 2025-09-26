import logging
from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form
from utils.document_processor import DocumentProcessor
from utils.pinecone_manager import PineconeManager

@router.post("/add-document")
async def add_document_vector_store(file: UploadFile = File(...), namespace: str = Form(...)):
    logger.info(f"Received request to add document '{file.filename}' to namespace: {namespace}")
    try:
        document_processor = DocumentProcessor()
        if not namespace:
            logger.error(f"Missing namespace: {namespace}")
            raise HTTPException(status_code=400, detail="namespace is required")

        logger.info(f"Validated namespace: '{namespace}'")
        pinecone_manager = PineconeManager(namespace)
        has_vectors = pinecone_manager.namespace_has_vectors()
        logger.info(f"Extracting text from document: {file.filename}")
        extracted_text = await document_processor.extract_text_from_file(file)

        if not extracted_text.strip():
            logger.error("Document contains no extractable text")
            raise HTTPException(status_code=400, detail="Documento não contém texto extraível")
        logger.info(f"Adding document to {'existing' if has_vectors else 'new'} namespace: {namespace}")

        pinecone_manager.add_documents([extracted_text])
        return f"Successfully processed document '{file.filename}' for namespace '{namespace}'"
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in add-document route: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.post("/clean-namespace")
async def clean_namespace(request: Request):
    body = await request.json()
    namespace = body.get("namespace")

    if not namespace:
        logger.error(f"Missing namespace in request: {body}")
        raise HTTPException(status_code=400, detail="namespace is required")
    logger.info(f"Received request to clean namespace: {namespace}")

    try:
        pinecone_manager = PineconeManager(namespace)
        return pinecone_manager.delete_all_vectors()
    except HTTPException as e:
        logger.error(f"Error: {e}")
        raise
    except Exception as e:
        logger.error(f"Error in route clean-namespace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")