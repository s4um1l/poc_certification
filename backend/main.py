import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel # No longer needed directly if all models imported
import uvicorn
from app.agent import get_agent_response, agent_app
from typing import Dict, Any, List, Literal # Keep for type hinting if used outside models
import json
import logging
from contextlib import asynccontextmanager
# from vercel_ai.fastapi import StreamingTextResponse # Commenting out Vercel specific
from starlette.responses import StreamingResponse # Using Starlette's generic StreamingResponse
from pydantic import BaseModel # Add Pydantic BaseModel if not already explicitly imported for new model

# Import models from app.models
from app.models import (
    QueryRequest, 
    MessageVercelAI, 
    ChatRequestVercelAI, 
    ToolUsage, 
    DebugInfo, 
    AgentLogicResponse
)

# Import RAG setup functions and the agent module using relative paths
# since main.py is run from within the backend directory
from data_processing import setup_vector_store
from tools import create_query_internal_docs_tool
from app import agent as agent_module # To access agent_module.instrumented_tools

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # --- Startup ---
        logger.info("Application startup: Initializing RAG retriever and tool...")
        retriever = setup_vector_store()
        if retriever:
            agent_module.rag_retriever = retriever # Store retriever if needed elsewhere
            rag_tool = create_query_internal_docs_tool(retriever)
            if rag_tool:
                logger.info(f"RAG tool '{rag_tool.name}' created successfully.")
                # Append the raw RAG tool directly to the agent's tool list
                # No instrumentation needed here anymore
                agent_module.tools.append(rag_tool)
                logger.info(f"Appended '{rag_tool.name}' to agent_module.tools. Current tools: {[t.name for t in agent_module.tools]}")
            else:
                logger.error("Failed to create RAG tool from retriever.")
        else:
            logger.error("RAG retriever initialization failed. RAG tool will not be available.")

        yield
        # --- Shutdown ---
        logger.info("Application shutdown.")
        # Add any cleanup logic here if needed

    except Exception as e:
        logger.critical(f"Critical error during RAG setup on application startup: {e}", exc_info=True)
        # Depending on policy, either raise the exception to stop the app
        # or yield to allow the app to start without the RAG tool.
        # Raising is safer if RAG is critical.
        # raise # Uncomment to prevent app start on critical RAG error
        yield # Allow app to start but RAG tool might be missing


# Create FastAPI app with lifespan manager
app = FastAPI(
    title="AI COO Shopify Agent",
    description="An AI agent that provides insights about sales velocity and inventory levels.",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS
origins = [
    "http://localhost:3000",  # Next.js default port
    "http://localhost:5173",  # Vite default port
    # Add your deployed frontend URL when available
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/")
async def read_root():
    return {
        "status": "ok",
        "message": "AI COO Agent Backend is running"
    }

# Detailed debug information endpoint
@app.post("/api/debug")
async def debug_agent(request: QueryRequest):
    try:
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # Create the initial state
        from langchain_core.messages import HumanMessage
        initial_state = {
            "messages": [HumanMessage(content=request.query)],
        }
        
        # Enable full trace
        config = {"recursion_limit": 25, "traceable": True}
        
        # Run the agent
        result = agent_app.invoke(initial_state, config=config)
        
        # Examine each message
        message_data = []
        for i, msg in enumerate(result["messages"]):
            msg_info = {
                "index": i,
                "type": type(msg).__name__,
                "content": getattr(msg, "content", None),
                "has_tool_calls": hasattr(msg, "tool_calls"),
                "has_tool_call_results": hasattr(msg, "tool_call_results"),
            }
            
            # If it has tool calls, extract them
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                tool_calls = []
                for tc in msg.tool_calls:
                    tc_info = {
                        "type": type(tc).__name__,
                        "name": getattr(tc, "name", None),
                        "args": getattr(tc, "args", None),
                        "id": getattr(tc, "id", None),
                    }
                    tool_calls.append(tc_info)
                msg_info["tool_calls"] = tool_calls
            
            # If it has tool call results, extract them
            if hasattr(msg, "tool_call_results") and msg.tool_call_results:
                tool_results = []
                for tr in msg.tool_call_results:
                    tr_info = {
                        "type": type(tr).__name__,
                        "value": tr,
                    }
                    tool_results.append(tr_info)
                msg_info["tool_call_results"] = tool_results
            
            message_data.append(msg_info)
        
        # Get trace if available
        trace_data = None
        if hasattr(agent_app, "get_trace"):
            try:
                trace_data = agent_app.get_trace(initial_state)
                # Convert to JSON-serializable format
                trace_data = json.loads(json.dumps(trace_data, default=str))
            except Exception as e:
                trace_data = {"error": str(e)}
        
        return {
            "response": result["messages"][-1].content if result["messages"] else "",
            "message_data": message_data,
            "message_count": len(result["messages"]),
            "trace_data": trace_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Define a Pydantic model for the /api/test_rag request
class RAGTestRequest(BaseModel):
    query: str

# New endpoint to directly test RAG
@app.post("/api/test_rag")
async def test_rag_tool(request: RAGTestRequest):
    if not agent_module.rag_retriever:
        logger.error("/api/test_rag called but RAG retriever is not initialized.")
        raise HTTPException(status_code=503, detail="RAG retriever is not available or not initialized.")
    
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    logger.info(f"/api/test_rag called with query: '{request.query}'")
    try:
        retrieved_docs = await agent_module.rag_retriever.ainvoke(request.query)
        contexts = [doc.page_content for doc in retrieved_docs]
        
        answer = ""
        if contexts:
            answer = "\\n\\n---\\n\\n".join(contexts)
            logger.info(f"/api/test_rag: Retrieved {len(contexts)} contexts.")
        else:
            answer = "No relevant documents found for the query."
            logger.info("/api/test_rag: No contexts retrieved.")
            
        return {"answer": answer, "contexts": contexts}
    except Exception as e:
        logger.error(f"Error in /api/test_rag for query '{request.query}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing RAG request: {str(e)}")

# Chat endpoint - MODIFIED
@app.post("/api/chat")
async def chat_with_agent_sdk(request: ChatRequestVercelAI): # Uses ChatRequestVercelAI from app.models
    try:
        if not request.messages:
            raise HTTPException(status_code=400, detail="No messages provided")

        last_message = request.messages[-1]
        if last_message.role != 'user':
            raise HTTPException(status_code=400, detail="Last message in the request must be from the user.")
        
        user_query = last_message.content
        if not user_query.strip():
            raise HTTPException(status_code=400, detail="User query content cannot be empty")

        # get_agent_response will now return an AgentLogicResponse Pydantic model instance
        agent_response_obj: AgentLogicResponse = get_agent_response(user_query)
        
        # Log the Pydantic model (optional, but can be useful)
        # logger.info(f"AgentLogicResponse object: {agent_response_obj.model_dump_json(indent=2)}")

        response_content = agent_response_obj.response # Access via attribute
        logger.info(f"Preparing to stream response content: '{response_content}'") # Log the content

        async def content_stream():
            if response_content: # Check if there is content to send
                # Format according to Vercel AI SDK text streaming convention
                yield f"0:{json.dumps(response_content)}\n"
            # else: yield nothing or an empty marker if required by protocol

        return StreamingResponse(content_stream(), media_type="text/plain")

    except HTTPException: # Re-raise HTTPExceptions directly
        raise
    except Exception as e:
        logger.error(f"Error in /api/chat (SDK): {e}", exc_info=True) # Keep exc_info for full traceback
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

# Create a .env file if it doesn't exist
if not os.path.exists(".env"):
    with open(".env", "w") as f:
        f.write("# Add your API keys here\n")
        f.write("# OPENAI_API_KEY=your-key-here\n")
        f.write("# ANTHROPIC_API_KEY=your-key-here\n")

# Run the app with uvicorn when executed directly
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 