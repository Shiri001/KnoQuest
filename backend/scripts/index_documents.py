import os
import re
import sys
import logging
from typing import List, Dict, Any, Optional

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env")))

from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("knoquest.indexer")

def get_openai_client():
    """Initializes AzureOpenAI client with API key or DefaultAzureCredential."""
    endpoint = settings.AZURE_OPENAI_ENDPOINT or settings.AZURE_PROJECT_ENDPOINT
    if not endpoint:
        logger.warning("No Azure OpenAI or Foundry endpoint configured.")
        return None

    try:
        from openai import AzureOpenAI
        if settings.AZURE_OPENAI_API_KEY:
            logger.info("Using AZURE_OPENAI_API_KEY for embedding generation.")
            client = AzureOpenAI(
                azure_endpoint=endpoint,
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION
            )
        else:
            logger.info("Testing DefaultAzureCredential for embedding generation...")
            from azure.identity import DefaultAzureCredential, get_bearer_token_provider
            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(),
                "https://cognitiveservices.azure.com/.default"
            )
            client = AzureOpenAI(
                azure_endpoint=endpoint,
                azure_ad_token_provider=token_provider,
                api_version=settings.AZURE_OPENAI_API_VERSION
            )

        # Quick validation ping to confirm authentication works
        client.embeddings.create(input="test", model=settings.AZURE_EMBEDDING_DEPLOYMENT_NAME)
        logger.info("Azure OpenAI embedding authentication verified successfully!")
        return client
    except Exception as e:
        logger.warning(
            f"Azure OpenAI embedding authentication unavailable: {e}.\n"
            f"Note: To enable vector embeddings, provide AZURE_OPENAI_API_KEY in backend/.env.\n"
            f"Proceeding with text/keyword indexing into Azure AI Search..."
        )
        return None

def generate_embedding(text: str, client) -> Optional[List[float]]:
    """Generates embedding vector using text-embedding-3-large."""
    if not client:
        return None
    try:
        response = client.embeddings.create(
            input=text,
            model=settings.AZURE_EMBEDDING_DEPLOYMENT_NAME
        )
        return response.data[0].embedding
    except Exception as e:
        logger.warning(f"Embedding generation error for model '{settings.AZURE_EMBEDDING_DEPLOYMENT_NAME}': {e}")
        return None

def ensure_search_index(index_name: str):
    """Creates or updates the Azure AI Search index with vector search configuration."""
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents.indexes import SearchIndexClient
    from azure.search.documents.indexes.models import (
        SearchIndex,
        SimpleField,
        SearchableField,
        SearchField,
        SearchFieldDataType,
        VectorSearch,
        HnswAlgorithmConfiguration,
        VectorSearchProfile,
        VectorSearchAlgorithmMetric,
    )

    if not settings.AZURE_SEARCH_ENDPOINT or not settings.AZURE_SEARCH_API_KEY:
        raise ValueError("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_API_KEY must be set.")

    index_client = SearchIndexClient(
        endpoint=settings.AZURE_SEARCH_ENDPOINT,
        credential=AzureKeyCredential(settings.AZURE_SEARCH_API_KEY)
    )

    fields = [
        SimpleField(name="chunk_id", type=SearchFieldDataType.String, key=True, filterable=True),
        SearchableField(name="source", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SearchableField(name="section", type=SearchFieldDataType.String, filterable=True),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=settings.AZURE_EMBEDDING_DIMENSIONS,
            vector_search_profile_name="knoquest-vector-profile"
        )
    ]

    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="knoquest-hnsw-algorithm",
                parameters={
                    "metric": VectorSearchAlgorithmMetric.COSINE,
                    "m": 4,
                    "efConstruction": 400,
                    "efSearch": 500
                }
            )
        ],
        profiles=[
            VectorSearchProfile(
                name="knoquest-vector-profile",
                algorithm_configuration_name="knoquest-hnsw-algorithm"
            )
        ]
    )

    index = SearchIndex(name=index_name, fields=fields, vector_search=vector_search)
    logger.info(f"Creating or updating Azure AI Search index '{index_name}'...")
    index_client.create_or_update_index(index)
    logger.info(f"Azure AI Search index '{index_name}' is ready.")

def split_into_sections(text: str, filename: str) -> List[tuple]:
    """Splits document text into logical sections based on headers."""
    lines = text.splitlines()
    sections = []
    current_title = "Overview / Preamble"
    current_lines = []

    for line in lines:
        header_match = re.match(r'^(SECTION\s+\d+[:\-\s].*|^\d+\.\d+\s+.*)', line.strip(), re.IGNORECASE)
        if header_match and len(current_lines) > 2:
            sections.append((current_title, "\n".join(current_lines)))
            current_title = line.strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_title, "\n".join(current_lines)))

    return sections

def clean_chunk_id(raw_id: str) -> str:
    """Azure AI Search keys allow only letters, digits, underscores, dashes, and equal signs."""
    return re.sub(r'[^a-zA-Z0-9_\-=]', '_', raw_id)

def run_ingestion():
    """Main ingestion runner."""
    docs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "enterprise_docs"))
    if not os.path.exists(docs_dir):
        logger.error(f"Documents directory '{docs_dir}' does not exist.")
        return False

    index_name = settings.AZURE_SEARCH_INDEX_NAME
    ensure_search_index(index_name)

    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient

    search_client = SearchClient(
        endpoint=settings.AZURE_SEARCH_ENDPOINT,
        index_name=index_name,
        credential=AzureKeyCredential(settings.AZURE_SEARCH_API_KEY)
    )

    openai_client = get_openai_client()
    doc_files = [f for f in os.listdir(docs_dir) if f.endswith(('.txt', '.pdf', '.docx'))]
    logger.info(f"Found {len(doc_files)} policy documents in {docs_dir}.")

    documents_to_upload = []
    vector_count = 0

    for filename in doc_files:
        file_path = os.path.join(docs_dir, filename)
        text = ""
        if filename.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
        elif filename.endswith('.pdf'):
            try:
                from pypdf import PdfReader
                reader = PdfReader(file_path)
                text = "\n".join([page.extract_text() or "" for page in reader.pages])
            except Exception as e:
                logger.error(f"Error reading PDF {filename}: {e}")
                continue
        elif filename.endswith('.docx'):
            try:
                import docx
                doc = docx.Document(file_path)
                text = "\n".join([p.text for p in doc.paragraphs])
            except Exception as e:
                logger.error(f"Error reading DOCX {filename}: {e}")
                continue

        sections = split_into_sections(text, filename)
        for i, (sec_title, sec_text) in enumerate(sections):
            raw_chunk_id = f"{filename}#sec_{i+1}"
            chunk_id = clean_chunk_id(raw_chunk_id)
            content = sec_text.strip()
            
            # Generate embedding if client available
            vector = None
            if openai_client:
                vector = generate_embedding(f"{sec_title}: {content}", openai_client)
                if vector:
                    vector_count += 1

            doc_payload = {
                "chunk_id": chunk_id,
                "source": filename,
                "section": sec_title,
                "content": content
            }
            if vector is not None:
                doc_payload["content_vector"] = vector

            documents_to_upload.append(doc_payload)

    logger.info(f"Prepared {len(documents_to_upload)} chunks ({vector_count} with vectors). Uploading to Azure Search...")
    
    # Upload in batches of 50
    batch_size = 50
    for i in range(0, len(documents_to_upload), batch_size):
        batch = documents_to_upload[i:i + batch_size]
        results = search_client.merge_or_upload_documents(documents=batch)
        succeeded = sum(1 for r in results if r.succeeded)
        logger.info(f"Batch {i // batch_size + 1}: {succeeded}/{len(batch)} chunks uploaded successfully.")

    logger.info(f"Ingestion completed successfully! Total chunks in index: {len(documents_to_upload)}")
    return True

if __name__ == "__main__":
    success = run_ingestion()
    sys.exit(0 if success else 1)
