import os
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import Qdrant
from qdrant_client import QdrantClient, models
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Determine script directory for robust path construction
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Configuration
KNOWLEDGE_BASE_DIR = os.path.join(SCRIPT_DIR, "knowledge_base") # Path relative to this script
QDRANT_PATH = os.path.join(SCRIPT_DIR, "qdrant_db") # Path relative to this script
COLLECTION_NAME = "internal_docs"
EMBEDDING_MODEL = "s4um1l/saumil-ft-633e5453-0b3a-4693-9108-c6cc8a87730f"
CHUNK_SIZE = 700
CHUNK_OVERLAP = 50
VECTOR_SIZE = 384


def setup_vector_store():
    """
    Loads documents from the knowledge base, chunks them, generates embeddings,
    and sets up a persistent Qdrant vector store.
    """
    logger.info(f"Knowledge base directory configured to: {KNOWLEDGE_BASE_DIR}")
    logger.info(f"Qdrant database path configured to: {QDRANT_PATH}")
    
    logger.info(f"Initializing embedding model: {EMBEDDING_MODEL}")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    vectorstore = None
    client = None # Define client outside try/except to ensure it's available if needed later

    # Determine if the database directory exists. If not, we are definitely creating.
    db_dir_exists = os.path.exists(QDRANT_PATH)
    
    try:
        logger.info(f"Attempting to initialize QdrantClient with path: {QDRANT_PATH}")
        client = QdrantClient(path=QDRANT_PATH)
        
        try:
            client.get_collection(collection_name=COLLECTION_NAME)
            logger.info(f"Collection '{COLLECTION_NAME}' found. Initializing Qdrant wrapper.")
            vectorstore = Qdrant(
                client=client,
                collection_name=COLLECTION_NAME,
                embeddings=embeddings
            )
            logger.info("Successfully loaded existing vector store.")
            return vectorstore.as_retriever() # Successfully loaded existing store

        except ValueError as e: # Specifically catch "Collection not found"
            if "not found" in str(e).lower():
                logger.info(f"Collection '{COLLECTION_NAME}' not found. Proceeding to create and populate.")
                # Collection doesn't exist, but client is initialized. We can use this client.
                pass # Proceed to document loading and collection creation with this client
            else:
                raise # Re-raise other ValueErrors

    except Exception as e: # Handles other QdrantClient connection errors or unexpected issues
        logger.warning(f"Initial QdrantClient connection/check failed (Reason: {e}). Will attempt fresh creation.")
        # If client initialization failed, ensure it's None so we don't try to use a broken client.
        client = None 
        # If db_dir_exists was true but client init failed, it might be corrupted.
        # It's safer to proceed as if we're creating from scratch.

    # If we've reached here, it means either:
    # 1. The collection was not found (client is valid).
    # 2. Initial client connection/check failed (client is None, or we want to ignore it).
    # In either case, we attempt to create/recreate the collection and populate.

    try:
        logger.info(f"Loading documents from: {KNOWLEDGE_BASE_DIR}")
        loader = DirectoryLoader(
            KNOWLEDGE_BASE_DIR, glob="**/*.txt", loader_cls=TextLoader, show_progress=True
        )
        documents = loader.load()

        if not client: # If initial client creation failed, try creating one now for the new DB
            logger.info("Re-initializing QdrantClient for new database creation.")
            client = QdrantClient(path=QDRANT_PATH) # This might recreate the db dir if deleted

        # Ensure collection exists (or create it)
        try:
            client.get_collection(collection_name=COLLECTION_NAME)
            logger.info(f"Collection '{COLLECTION_NAME}' seems to exist after all. Using it.")
        except ValueError: # Collection not found
            logger.info(f"Creating collection '{COLLECTION_NAME}'.")
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=models.VectorParams(size=VECTOR_SIZE, distance=models.Distance.COSINE)
            )

        if not documents:
            logger.warning(f"No documents found in {KNOWLEDGE_BASE_DIR}. Collection '{COLLECTION_NAME}' will be empty (or remain as is if it existed).")
            # Initialize Qdrant wrapper for the (potentially empty) collection
            vectorstore = Qdrant(client=client, collection_name=COLLECTION_NAME, embeddings=embeddings)
        else:
            logger.info(f"Loaded {len(documents)} documents.")
            text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
                chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP, disallowed_special=()
            )
            doc_splits = text_splitter.split_documents(documents)
            logger.info(f"Split documents into {len(doc_splits)} chunks.")
            
            logger.info(f"Initializing Qdrant wrapper for collection '{COLLECTION_NAME}' before adding documents.")
            vectorstore = Qdrant(
                client=client,
                collection_name=COLLECTION_NAME,
                embeddings=embeddings
            )
            logger.info(f"Adding {len(doc_splits)} document chunks to collection '{COLLECTION_NAME}'...")
            # Use the add_documents method of the Langchain Qdrant wrapper
            vectorstore.add_documents(doc_splits)
            logger.info(f"Successfully added documents to collection '{COLLECTION_NAME}'.")

    except Exception as creation_e:
        logger.error(f"CRITICAL FAILURE during collection creation/population: {creation_e}", exc_info=True)
        return None

    if not vectorstore:
        logger.error("Vectorstore initialization failed. RAG tool will not be available.")
        return None

    return vectorstore.as_retriever()


if __name__ == "__main__":
    # Example usage when running this script directly
    logger.info("Setting up vector store directly (example run)...")
    retriever = setup_vector_store()
    if retriever:
        logger.info("Vector store setup complete. Retriever is ready.")
        # Example query
        try:
            # Make sure knowledge base has some text files for this to work
            # For example, create a file in backend/knowledge_base/sample.txt with "FastAPI is a web framework."
            if not os.path.exists(os.path.join(KNOWLEDGE_BASE_DIR, "sample.txt")):
                 os.makedirs(KNOWLEDGE_BASE_DIR, exist_ok=True)
                 with open(os.path.join(KNOWLEDGE_BASE_DIR, "sample.txt"), "w") as f:
                     f.write("FastAPI is a web framework. Qdrant is a vector database.")
                 logger.info(f"Created {os.path.join(KNOWLEDGE_BASE_DIR, 'sample.txt')} for example query.")

            results = retriever.invoke("What is FastAPI?")
            logger.info(f"Example query results: {results}")
            results_qdrant = retriever.invoke("Tell me about Qdrant.")
            logger.info(f"Example query results for Qdrant: {results_qdrant}")

        except Exception as e:
            logger.error(f"Error running example query: {e}")
            logger.error("Ensure there are .txt files in the knowledge_base directory for the example to work.")
    else:
        logger.error("Failed to set up vector store during example run.") 