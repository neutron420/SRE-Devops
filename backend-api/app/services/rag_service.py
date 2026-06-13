import os
import uuid
import logging
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.api.types import Documents, Embeddings, EmbeddingFunction
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

# Custom Embedding Function using SentenceTransformers
class SentenceTransformerEmbeddingFunction(EmbeddingFunction):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        logger.info(f"Initializing SentenceTransformer model: {model_name}")
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
        except ImportError:
            logger.error("sentence-transformers package is missing! Please install it.")
            raise

    def __call__(self, input: Documents) -> Embeddings:
        # Generate embeddings and convert to a list of lists of floats
        embeddings = self.model.encode(input, convert_to_numpy=True)
        return embeddings.tolist()

class RAGService:
    """
    RAG Service layer to ingest documents (PDFs, Markdown, text files),
    chunk them using RecursiveCharacterTextSplitter, generate embeddings,
    store them in ChromaDB, and query them.
    """

    def __init__(self):
        self.persist_dir = os.getenv("CHROMADB_PERSIST_DIRECTORY", "./vector-db/chroma_data")
        os.makedirs(self.persist_dir, exist_ok=True)
        
        logger.info(f"Connecting to ChromaDB at {self.persist_dir}")
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        
        # Initialize embedding function
        self.embedding_function = SentenceTransformerEmbeddingFunction()
        
        # Get or create the collection
        self.collection_name = "sre_runbooks"
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function
        )
        logger.info(f"ChromaDB collection '{self.collection_name}' initialized.")

    def chunk_text(self, text: str, chunk_size: int = 800, chunk_overlap: int = 100) -> List[str]:
        """
        Splits text into chunks using LangChain's RecursiveCharacterTextSplitter.
        """
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len
        )
        return splitter.split_text(text)

    def add_document(self, content: str, filename: str, doc_type: str = "txt", metadata: Optional[Dict[str, Any]] = None) -> int:
        """
        Chunks and adds a document to ChromaDB.
        """
        logger.info(f"Ingesting file '{filename}' ({doc_type}) into RAG Service")
        
        chunks = self.chunk_text(content)
        if not chunks:
            logger.warning(f"Document '{filename}' is empty, skipping ingestion.")
            return 0

        ids = []
        documents = []
        metadatas = []
        
        base_meta = metadata or {}
        base_meta.update({
            "filename": filename,
            "doc_type": doc_type
        })

        for index, chunk in enumerate(chunks):
            chunk_id = f"{filename}_{uuid.uuid4().hex[:8]}_chunk_{index}"
            ids.append(chunk_id)
            documents.append(chunk)
            
            # Make sure metadata values are primitive types for ChromaDB compatibility
            chunk_meta = base_meta.copy()
            chunk_meta["chunk_index"] = index
            metadatas.append(chunk_meta)

        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        logger.info(f"Successfully added {len(chunks)} chunks for '{filename}' to vector store.")
        return len(chunks)

    def upload_and_index_file(self, file_bytes: bytes, file_name: str) -> int:
        """
        Parses raw bytes of a PDF, Markdown, or text file and indexes it in the vector DB.
        """
        file_ext = file_name.split(".")[-1].lower()
        content = ""

        if file_ext == "pdf":
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                for page in doc:
                    content += page.get_text()
            except ImportError:
                raise ImportError("PyMuPDF (fitz) is required to parse PDF files.")
            except Exception as e:
                logger.error(f"Error parsing PDF file '{file_name}': {str(e)}")
                raise
        elif file_ext in ["md", "markdown", "txt", "log", "json", "yaml", "yml"]:
            try:
                content = file_bytes.decode("utf-8", errors="ignore")
            except Exception as e:
                logger.error(f"Error reading text file '{file_name}': {str(e)}")
                raise
        else:
            raise ValueError(f"Unsupported file format: '.{file_ext}'")

        return self.add_document(content=content, filename=file_name, doc_type=file_ext)

    def search_documents(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Queries ChromaDB for similar text chunks.
        """
        logger.info(f"Querying vector store for: '{query}'")
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=limit
            )
            
            formatted_results = []
            if not results or not results["documents"] or len(results["documents"][0]) == 0:
                return []
                
            docs = results["documents"][0]
            metas = results["metadatas"][0] if results["metadatas"] else [{}] * len(docs)
            ids = results["ids"][0]
            distances = results["distances"][0] if results["distances"] else [0.0] * len(docs)

            for doc, meta, cid, dist in zip(docs, metas, ids, distances):
                formatted_results.append({
                    "id": cid,
                    "content": doc,
                    "metadata": meta,
                    "distance": float(dist)
                })
            return formatted_results
        except Exception as e:
            logger.error(f"Error querying vector store: {str(e)}")
            return []
