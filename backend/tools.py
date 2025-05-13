from langchain.tools.retriever import create_retriever_tool
from langchain_core.retrievers import BaseRetriever
import logging

logger = logging.getLogger(__name__)

def create_query_internal_docs_tool(retriever: BaseRetriever):
    """
    Creates a RAG tool for querying internal documents.

    Args:
        retriever: The retriever instance for the internal document vector store.

    Returns:
        A Langchain tool for querying internal documents.
    """
    if retriever is None:
        logger.error("Retriever is None. Cannot create query_internal_docs_tool.")
        # Return a dummy tool or raise an error
        # This could happen if setup_vector_store found no documents
        # and was modified to return None.
        # For now, let's assume we'd want the application to be aware of this.
        raise ValueError("Retriever cannot be None when creating the RAG tool.")

    tool_name = "query_internal_documents"
    tool_description = (
        "Search and retrieve information from internal knowledge base documents. "
        "Use this tool when you need to answer questions based on proprietary or specific internal data. "
        "Input should be a clear question or search query."
    )

    logger.info(f"Creating RAG tool: {tool_name} with retriever: {type(retriever)}")
    return create_retriever_tool(
        retriever,
        tool_name,
        tool_description,
    )

# Example of how other tools might be defined in this file (if any)
# from langchain_core.tools import tool
# @tool
# def another_tool(query: str) -> str:
#     \"\"\"A placeholder for another tool.\"\"\" 
#     return f\"Another tool received: {query}\"\" 