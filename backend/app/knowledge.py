import os
import re
import math
import logging
from typing import List, Dict, Any, Optional
from collections import Counter
from .config import settings
from .models.schemas import SourceCitation

logger = logging.getLogger("knoquest.knowledge")

class DocumentChunk:
    def __init__(self, chunk_id: str, source: str, section: str, content: str):
        self.chunk_id = chunk_id
        self.source = source
        self.section = section
        self.content = content

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "source": self.source,
            "section": self.section,
            "content": self.content
        }

class KnowledgeBase:
    """
    Enterprise Knowledge Retrieval Engine for NovaTech Solutions.
    Provides dual-engine capability:
    - Azure AI Search (when configured in .env)
    - Resilient Local BM25/Cosine Index (always ready, zero external dependencies)
    """

    def __init__(self):
        self.docs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "enterprise_docs"))
        self.chunks: List[DocumentChunk] = []
        self.session_chunks: Dict[str, List[DocumentChunk]] = {}  # session_id -> list of chunks
        self.is_azure_search_ready = False
        self.azure_search_client = None
        self.openai_client = None
        self.is_embedding_ready = False

        # Build initial index
        self.load_and_index_documents()
        self._init_azure_search()

    def _init_azure_search(self):
        if not settings.AZURE_MODE or not settings.AZURE_SEARCH_ENDPOINT:
            return

        try:
            from azure.core.credentials import AzureKeyCredential
            from azure.search.documents import SearchClient

            if settings.AZURE_SEARCH_API_KEY:
                credential = AzureKeyCredential(settings.AZURE_SEARCH_API_KEY)
                self.azure_search_client = SearchClient(
                    endpoint=settings.AZURE_SEARCH_ENDPOINT,
                    index_name=settings.AZURE_SEARCH_INDEX_NAME,
                    credential=credential
                )
                self.is_azure_search_ready = True
                logger.info(f"Connected to Azure AI Search service index '{settings.AZURE_SEARCH_INDEX_NAME}'.")
        except Exception as e:
            logger.warning(f"Could not connect to Azure AI Search: {e}.")
            self.is_azure_search_ready = False

        # Initialize embedding client if endpoint configured
        endpoint = settings.AZURE_OPENAI_ENDPOINT or settings.AZURE_PROJECT_ENDPOINT
        if endpoint:
            try:
                from openai import AzureOpenAI
                if settings.AZURE_OPENAI_API_KEY:
                    self.openai_client = AzureOpenAI(
                        azure_endpoint=endpoint,
                        api_key=settings.AZURE_OPENAI_API_KEY,
                        api_version=settings.AZURE_OPENAI_API_VERSION
                    )
                else:
                    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
                    token_provider = get_bearer_token_provider(
                        DefaultAzureCredential(),
                        "https://cognitiveservices.azure.com/.default"
                    )
                    self.openai_client = AzureOpenAI(
                        azure_endpoint=endpoint,
                        azure_ad_token_provider=token_provider,
                        api_version=settings.AZURE_OPENAI_API_VERSION
                    )
                # Quick test
                self.openai_client.embeddings.create(input="healthcheck", model=settings.AZURE_EMBEDDING_DEPLOYMENT_NAME)
                self.is_embedding_ready = True
                logger.info(f"Azure OpenAI embedding model '{settings.AZURE_EMBEDDING_DEPLOYMENT_NAME}' verified.")
            except Exception as e:
                logger.warning(f"Embedding model initialization notice: {e}. Running in keyword-search mode for Azure Search.")
                self.is_embedding_ready = False

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generates embedding vector via text-embedding-3-large if available."""
        if not self.is_embedding_ready or not self.openai_client:
            return None
        try:
            resp = self.openai_client.embeddings.create(
                input=text,
                model=settings.AZURE_EMBEDDING_DEPLOYMENT_NAME
            )
            return resp.data[0].embedding
        except Exception as e:
            logger.warning(f"Failed to generate embedding for query: {e}")
            return None

    def load_and_index_documents(self):
        """Loads all policy documents from data/enterprise_docs and chunks them."""
        self.chunks = []
        if not os.path.exists(self.docs_dir):
            os.makedirs(self.docs_dir, exist_ok=True)
            logger.warning(f"Documents directory {self.docs_dir} created.")
            return

        doc_files = [f for f in os.listdir(self.docs_dir) if f.endswith(('.txt', '.pdf', '.docx'))]
        for filename in doc_files:
            file_path = os.path.join(self.docs_dir, filename)
            self._process_document(file_path, filename)

        logger.info(f"Loaded {len(doc_files)} enterprise documents into {len(self.chunks)} semantic chunks.")

    def _process_document(self, file_path: str, filename: str):
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
                return
        elif filename.endswith('.docx'):
            try:
                import docx
                doc = docx.Document(file_path)
                text = "\n".join([p.text for p in doc.paragraphs])
            except Exception as e:
                logger.error(f"Error reading DOCX {filename}: {e}")
                return

        # Chunk by sections
        sections = self._split_into_sections(text, filename)
        for i, (sec_title, sec_text) in enumerate(sections):
            chunk_id = f"{filename}#sec_{i+1}"
            self.chunks.append(DocumentChunk(
                chunk_id=chunk_id,
                source=filename,
                section=sec_title,
                content=sec_text.strip()
            ))

    def _split_into_sections(self, text: str, filename: str) -> List[tuple]:
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

    def add_session_document(self, session_file_id: str, filename: str, content: str):
        """Indexes user-uploaded document for a specific session in memory and in Azure Search."""
        chunks = []
        sections = self._split_into_sections(content, filename)
        upload_docs = []
        for i, (sec_title, sec_text) in enumerate(sections):
            raw_chunk_id = f"{session_file_id}_{filename}_sec_{i+1}"
            chunk_id = re.sub(r'[^a-zA-Z0-9_\-=]', '_', raw_chunk_id)
            sec_clean = sec_text.strip()
            chunks.append(DocumentChunk(
                chunk_id=chunk_id,
                source=filename,
                section=sec_title,
                content=sec_clean
            ))
            doc_item = {
                "chunk_id": chunk_id,
                "source": filename,
                "section": sec_title,
                "content": sec_clean
            }
            if self.is_embedding_ready:
                vec = self.generate_embedding(f"{sec_title}: {sec_clean}")
                if vec:
                    doc_item["content_vector"] = vec
            upload_docs.append(doc_item)

        self.session_chunks[session_file_id] = chunks
        logger.info(f"Added {len(chunks)} session chunks for {filename} (ID: {session_file_id}).")

        # Upload to Azure Search if active
        if self.is_azure_search_ready and self.azure_search_client and upload_docs:
            try:
                self.azure_search_client.merge_or_upload_documents(documents=upload_docs)
                logger.info(f"Uploaded {len(upload_docs)} session chunks to Azure Search.")
            except Exception as e:
                logger.warning(f"Failed to upload session chunks to Azure Search: {e}")

    def _tokenize(self, text: str) -> List[str]:
        return [w.lower() for w in re.findall(r'\b[a-zA-Z0-9_\-\$]+\b', text)]

    def search_knowledge(
        self,
        query: str,
        top_k: int = 3,
        session_file_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves the top-k most relevant policy chunks.
        When AZURE_MODE=true: Uses Azure AI Search (with vector/hybrid search when available).
        When AZURE_MODE=false: Uses local BM25 + Cosine relevance sandbox.
        """
        # 1. AZURE AI SEARCH PATH (when AZURE_MODE=true)
        if settings.AZURE_MODE:
            if not self.is_azure_search_ready or not self.azure_search_client:
                raise RuntimeError(
                    f"AZURE_MODE is true, but Azure AI Search is not ready. "
                    f"Please verify AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_API_KEY."
                )

            try:
                azure_hits = []
                
                # Check for active session uploaded chunks first if present
                if session_file_id and session_file_id in self.session_chunks:
                    for sc in self.session_chunks[session_file_id]:
                        if any(w in sc.content.lower() for w in query.lower().split() if len(w) > 3):
                            azure_hits.append({
                                "chunk_id": sc.chunk_id,
                                "source": sc.source,
                                "section": sc.section,
                                "content": sc.content,
                                "score": 2.0
                            })

                # Perform Hybrid Search (vector + keyword) or Keyword Search
                query_vector = self.generate_embedding(query) if self.is_embedding_ready else None
                if query_vector:
                    from azure.search.documents.models import VectorizedQuery
                    vq = VectorizedQuery(
                        vector=query_vector,
                        k_nearest_neighbors=top_k,
                        fields="content_vector"
                    )
                    results = self.azure_search_client.search(
                        search_text=query,
                        vector_queries=[vq],
                        top=top_k,
                        select=["chunk_id", "source", "section", "content"]
                    )
                else:
                    results = self.azure_search_client.search(
                        search_text=query,
                        top=top_k,
                        select=["chunk_id", "source", "section", "content"]
                    )

                for res in results:
                    azure_hits.append({
                        "chunk_id": res.get("chunk_id", ""),
                        "source": res.get("source", ""),
                        "section": res.get("section", ""),
                        "content": res.get("content", ""),
                        "score": res.get("@search.score", 1.0)
                    })

                return azure_hits[:top_k]
            except Exception as e:
                logger.error(f"Azure Search query error: {e}", exc_info=True)
                raise RuntimeError(f"Azure AI Search query failed: {e}")

        # 2. LOCAL SANDBOX PATH (when AZURE_MODE=false)
        candidate_chunks = list(self.chunks)
        if session_file_id and session_file_id in self.session_chunks:
            candidate_chunks = self.session_chunks[session_file_id] + candidate_chunks

        if not candidate_chunks:
            return []

        # 2. Local BM25 + Cosine Relevance Search
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        query_counter = Counter(query_tokens)
        query_len = math.sqrt(sum(c * c for c in query_counter.values())) or 1.0

        scores = []
        for chunk in candidate_chunks:
            full_text = f"{chunk.source} {chunk.section} {chunk.content}".lower()
            chunk_tokens = self._tokenize(full_text)
            chunk_counter = Counter(chunk_tokens)
            chunk_len = math.sqrt(sum(c * c for c in chunk_counter.values())) or 1.0

            # Cosine similarity
            dot_product = sum(query_counter[t] * chunk_counter[t] for t in query_tokens if t in chunk_counter)
            cosine_score = dot_product / (query_len * chunk_len)

            # Header / Section match bonus
            header_tokens = set(self._tokenize(chunk.section.lower()))
            header_overlap = sum(1 for t in query_tokens if t in header_tokens)
            if header_overlap > 0:
                cosine_score += (header_overlap * 0.25)

            # Exact multi-word phrase bonus
            clean_q = re.sub(r'[^a-zA-Z0-9\s]', '', query.lower()).strip()
            if len(clean_q) > 4 and clean_q in full_text:
                cosine_score += 0.4

            # Key terms boost (leave, wfh, hours, password, probation, incident, laptop, hotel, reimbursement, benefits, equipment)
            important_terms = [
                "leave", "remote", "wfh", "hours", "probation", "password", "mfa",
                "incident", "car", "travel", "reimbursement", "benefit", "benefits",
                "equipment", "replacement", "insurance"
            ]
            for term in important_terms:
                if term in query_tokens and term in full_text:
                    cosine_score += 0.15

            scores.append((cosine_score, chunk))

        scores.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, chunk in scores[:top_k]:
            if score > 0:
                results.append({
                    "chunk_id": chunk.chunk_id,
                    "source": chunk.source,
                    "section": chunk.section,
                    "content": chunk.content,
                    "score": round(score, 4)
                })

        return results

knowledge_base = KnowledgeBase()
