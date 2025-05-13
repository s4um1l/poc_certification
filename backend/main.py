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
from starlette.responses import StreamingResponse # Reverted to starlette
import asyncio

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

        logger.info(f"Received user query for streaming: {user_query}")

        async def event_stream_generator():
            # current_tool_calls_details maps llm_tool_call_id to {'name': tool_name, 'args_str': tool_args_str, 'type': 'function'}
            current_tool_calls_details = {} 
            # tool_id_for_index maps a tool_call_chunk's 'index' to its official 'tool_call_id'
            # tool_id_for_index = {}

            # logger.info("Using SUPER SIMPLE event_stream_generator for Vercel Data Protocol.")
            # yield f"0:{json.dumps(\"Hello from backend...\\n\")}\\n"
            # await asyncio.sleep(0.1) 
            # yield f"0:{json.dumps(\"This is message 1.\\n\")}\\n"
            # await asyncio.sleep(0.1)
            # yield f"0:{json.dumps(\"This is message 2.\\n\")}\\n"
            # await asyncio.sleep(0.1)
            # yield f"0:{json.dumps(\"Stream finished.\\n\")}\\n"
            # logger.info("SUPER SIMPLE event_stream_generator finished.")
            # return 

            logger.info(f"[{user_query}] Entering event_stream_generator with get_agent_response loop.")
            events_processed_count = 0
            has_yielded_first_contentful_text_chunk = False # New flag
            try:
                # Send a preliminary 2:data_json message - REMOVE THIS SECTION
                # control_message = {"type": "control", "data": "starting_text_stream"}
                # logger.info(f"[{user_query}] Yielding preliminary control message: {control_message}")
                # yield f"2:{json.dumps(control_message)}\\n"
                # logger.info(f"[{user_query}] Successfully yielded preliminary control message.")

                async for event in get_agent_response(user_query):
                    event_type = event["event"]
                    event_data = event["data"]
                    event_name = event.get("name", "N/A")
                    run_id = event.get("run_id", "N/A")
                    logger.info(f"[{user_query}] Received event from get_agent_response: type='{event_type}', name='{event_name}', run_id='{run_id}'")
                    # logger.debug(f"[{user_query}] Event data: {event_data}") # Can be very verbose

                    if event_type == "on_llm_stream" or event_type == "on_chat_model_stream":
                        logger.info(f"[{user_query}] Processing '{event_type}' for text content.")
                        chunk = event_data.get("chunk")
                        if chunk: # We have a chunk object
                            if hasattr(chunk, "content") and isinstance(chunk.content, str):
                                text_to_yield = chunk.content
                                
                                # Skip initial empty chunks until first contentful one
                                if not has_yielded_first_contentful_text_chunk and not text_to_yield.strip():
                                    logger.info(f"[{user_query}] Skipping initial empty text chunk from '{event_type}'.")
                                else:
                                    logger.info(f"[{user_query}] Preparing to yield text chunk (len={len(text_to_yield)}) from '{event_type}': {text_to_yield[:70]}...")
                                    yield f"0:{json.dumps(text_to_yield)}\\n"
                                    logger.info(f"[{user_query}] Successfully yielded text chunk (len={len(text_to_yield)}). Events processed: {events_processed_count + 1}")
                                    if not has_yielded_first_contentful_text_chunk and text_to_yield.strip():
                                        has_yielded_first_contentful_text_chunk = True
                                        logger.info(f"[{user_query}] First contentful text chunk yielded.")
                                    events_processed_count += 1
                            else:
                                logger.warning(f"[{user_query}] '{event_type}' chunk did not have a usable .content attribute or was not a string. Chunk type: {type(chunk)}, Chunk: {chunk}")
                        else:
                            logger.warning(f"[{user_query}] '{event_type}' had no 'chunk' in event_data.")
                    
                    elif event_type == "on_llm_end" or event_type == "on_chat_model_end":
                        logger.info(f"[{user_query}] Processing '{event_type}' event.")
                        output = event_data.get("output")
                        if output and hasattr(output, "tool_calls") and output.tool_calls:
                            # Tool call yielding (9:) is still commented out for this test
                            for tc_for_storage in output.tool_calls: 
                                if tc_for_storage.get("name") and tc_for_storage.get("id"):
                                    current_tool_calls_details[tc_for_storage["id"]] = {
                                        "name": tc_for_storage["name"],
                                        "args_str": json.dumps(tc_for_storage.get("args", {})), 
                                        "type": "function"
                                    }
                                    logger.info(f"[{user_query}] Stored tool call detail for ID: {tc_for_storage["id"]}")
                            events_processed_count += 1 # Count this as a processed event type

                    elif event_type == "on_chain_stream":
                        # Tool result yielding (a:) is still commented out for this test
                        logger.info(f"[{user_query}] Processing on_chain_stream event (tool results currently not yielded).")
                        # Minimal processing to store details if needed, similar to on_llm_end for current_tool_calls_details
                        events_processed_count += 1 # Count this as a processed event type
                        pass
                    
                    elif event_type == "on_tool_start":
                        logger.info(f"[{user_query}] Processing on_tool_start: {event_data.get('name')}")
                        events_processed_count += 1
                    
                    elif event_type == "on_tool_end":
                        logger.info(f"[{user_query}] Processing on_tool_end: {event_data.get('name')}")
                        events_processed_count += 1
                    
                    else:
                        logger.info(f"[{user_query}] Received unhandled event type: {event_type}")

                logger.info(f"[{user_query}] Exited get_agent_response loop. Total events processed for yielding/logging: {events_processed_count}")
            except Exception as e:
                logger.error(f"[{user_query}] Exception INSIDE event_stream_generator loop: {e}", exc_info=True)
                # Try to yield an error message to the client if possible
                error_payload = {"error": f"Error during agent processing: {str(e)}"}
                try:
                    yield f"0:{json.dumps(error_payload)}\\n"
                    logger.info(f"[{user_query}] Yielded error message to client due to internal exception.")
                except Exception as e_yield:
                    logger.error(f"[{user_query}] Failed to yield error message to client: {e_yield}", exc_info=True)
            finally:
                logger.info(f"[{user_query}] Event_stream_generator finally block. Processed {events_processed_count} yieldable events.")

        headers = {
            "X-Vercel-AI-Data-Stream": "v1",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
        return StreamingResponse(event_stream_generator(), media_type="text/plain; charset=utf-8", headers=headers)

    except HTTPException: 
        raise
    except Exception as e:
        logger.error(f"Error in /api/chat (SDK streaming): {e}", exc_info=True)
        async def error_stream():
            error_payload = {"type": "error", "message": "An internal server error occurred during streaming."}
            # Vercel uses '8' for general error messages in the stream data part
            # or a status code with a JSON body. Prefix '6' was from an old spec.
            # The AI SDK client might expect a JSON error object or a specific prefix like ' X-Experimental-Stream-Data-Error'.
            # For simplicity, using a generic JSON error that the frontend might try to parse or display.
            # Let's use a simple error message with prefix '0' assuming it might be displayed as text.
            # Or, consult Vercel AI SDK docs for their specific error streaming format.
            # Using the '6' prefix for now as it was in previous attempt, but needs verification.
            # AI SDK docs on Stream Protocols might clarify this.
            # Given the main content is text/plain, a prefixed error is common.
            yield f"0:{json.dumps({'error': 'An internal server error occurred.'})}\\n" # Simpler error as text
        return StreamingResponse(error_stream(), media_type="text/plain", status_code=500)

# Create a .env file if it doesn't exist
if not os.path.exists(".env"):
    with open(".env", "w") as f:
        f.write("# Add your API keys here\n")
        f.write("# OPENAI_API_KEY=your-key-here\n")
        f.write("# ANTHROPIC_API_KEY=your-key-here\n")

# Run the app with uvicorn when executed directly
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 