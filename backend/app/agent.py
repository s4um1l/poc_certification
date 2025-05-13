import os
import uuid
from typing import List, Dict, Any, Sequence, TypedDict, Callable, Optional, AsyncIterator
# Try to import Annotated from typing_extensions if not available in typing
try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated
from dotenv import load_dotenv
from operator import add
import copy
import json
import time

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.tools import BaseTool, tool

# Import both decorated and raw tool functions
from .tools import (
    get_product_info,
    list_products,
    get_inventory_level,
    list_low_stock_products,
    get_sales_data_for_product,
    estimate_days_of_stock_remaining,
    get_top_selling_products,
    # Add imports for the raw tool functions
    _get_product_info,
    _list_products,
    _get_inventory_level,
    _list_low_stock_products,
    _get_sales_data_for_product,
    _estimate_days_of_stock_remaining,
    _get_top_selling_products
)
from .tool_usage import reset_tracker, get_tool_usage, add_tool_usage
from .models import AgentLogicResponse, DebugInfo, ToolUsage # Added import

# Import for RAG - use relative imports as agent.py is inside 'app' which is inside 'backend'
# and backend/ is the root for python path when uvicorn starts from backend/
from data_processing import setup_vector_store
from tools import create_query_internal_docs_tool
import logging

logger = logging.getLogger(__name__)

# --- Initialize RAG Retriever and Tool (Placeholders) ---
# These will be populated during FastAPI startup via the lifespan event
rag_retriever = None
query_internal_docs_tool = None # Placeholder for the RAG tool

# Remove the create_instrumented_tool function entirely
# def create_instrumented_tool(original_tool):
#    ...

# List of raw tools (decorated functions or BaseTool instances)
# The RAG tool instance (query_internal_docs_tool) will be appended to this list
# by the lifespan event handler in main.py after it's created.
RAW_TOOLS: List[BaseTool] = [
    get_product_info,
    list_products,
    get_inventory_level,
    list_low_stock_products,
    get_sales_data_for_product,
    estimate_days_of_stock_remaining,
    get_top_selling_products
]
# Filter out any None entries just in case, although tools should be defined
RAW_TOOLS = [t for t in RAW_TOOLS if t is not None]

# The global `tools` variable will be this list, modified by main.py lifespan
tools = RAW_TOOLS

# Load environment variables
load_dotenv()

# Configure the LLM
def get_llm():
    """Get the LLM based on environment variables"""
    if os.environ.get("OPENAI_API_KEY"):
        return ChatOpenAI(model="gpt-4o", temperature=0)
    elif os.environ.get("ANTHROPIC_API_KEY"):
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model="claude-3-sonnet-20240229", temperature=0)
    else:
        raise ValueError("No API key found for OpenAI or Anthropic. Please set OPENAI_API_KEY or ANTHROPIC_API_KEY.")

# Define the agent state
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add]

# Define the tools (using the global `tools` list populated above and by lifespan)
# tools = instrumented_tools # No longer instrumenting

# System prompt template
SYSTEM_PROMPT = """
You are an AI Shopping Operations Assistant for a Shopify merchant. Your primary goal is to answer the merchant's questions accurately and efficiently.

You have access to specialized tools for specific data types and a general knowledge tool for policies, procedures, and other internal information.

{tool_descriptions}

## Tool Usage and Answering Protocol:

**1. Understand the Query Type:**
   - **Is it a request for specific, structured data?** (e.g., "What is the stock level for product X?", "Show me sales data for product Y.")
     - If YES, and it EXACTLY MATCHES one of the following, use the specific tool:
       - `get_product_info`: For specific product details by ID.
       - `list_products`: To see all available products.
       - `get_inventory_level`: For current stock levels by product ID.
       - `list_low_stock_products`: For products that need reordering.
       - `get_sales_data_for_product`: For historical sales data by product ID.
       - `estimate_days_of_stock_remaining`: To predict when items will run out.
       - `get_top_selling_products`: For bestseller analysis.
   - **Is it any other type of question?** (e.g., "How do I process a return?", "What is our policy on X?", "Explain concept Y.", or any query where you are uncertain).
     - If YES, **you MUST use the `query_internal_documents` tool.** This is your primary tool for all questions not covered by the highly specific data tools listed above.

**2. Tool Invocation and Response Generation:**
   - After invoking a tool, review the information received.
   - **If the information is sufficient to answer the user's question, formulate and provide the answer directly. Do NOT call another tool unless absolutely necessary to fulfill the original request.**
   - If the initial tool call (especially from `query_internal_documents`) does not provide a complete answer, you may re-phrase your query and try the *same* tool again if you believe more relevant information can be found within that tool's scope. Avoid rapidly switching between different tools for the same core question if the RAG tool is appropriate.

**3. Important Guidelines:**
   - **Prioritize `query_internal_documents`**: For any ambiguity or for questions about processes, policies, how-to guides, FAQs, or general knowledge, your FIRST and primary choice should be `query_internal_documents`.
   - **Accuracy is Key**: Always use tools to retrieve information. Do not invent answers.
   - **Clarify if Necessary**: If a specific data tool requires an ID (e.g., product ID) and it wasn't provided, ask for clarification *before* attempting to use the tool.
   - **Be Concise**: Provide clear and direct answers.
   - **Formatting**: Use $ for dollar amounts, % for percentages.

**Example Decision Flow:**
   - User asks: "What is the return policy for damaged goods?"
     - Agent identifies this as a policy question.
     - Agent Action: Call `query_internal_documents` with the query "return policy for damaged goods".
     - Agent Action: Formulate answer based on retrieved documents.

   - User asks: "How many units of 'Blue Widget' (ID: 123) do we have?"
     - Agent identifies this as a specific inventory query.
     - Agent Action: Call `get_inventory_level` with product ID 123.
     - Agent Action: Formulate answer based on tool output.

By following this protocol, you will efficiently use the available tools and provide accurate answers. If you find yourself calling multiple different tools for a single, simple query, re-evaluate if `query_internal_documents` should have been your primary choice.
"""

# Define the chatbot function using LLM with tools
def chatbot(state: AgentState):
    """Process the messages using the LLM"""
    llm = get_llm()
    # Bind the raw tools (populated globally) to the LLM
    # Ensure the global `tools` list is up-to-date (includes RAG tool from lifespan)
    llm_with_tools = llm.bind_tools(tools)

    # Create prompt template with system message
    # Use the current state of the global `tools` list for descriptions
    tool_descriptions = "\n".join([f"- {tool.name}: {tool.description}" for tool in tools if tool is not None])
    messages = state["messages"]
    
    # Use a system message and the history
    system_message = SYSTEM_PROMPT.format(tool_descriptions=tool_descriptions)
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("placeholder", "{messages}"),
    ])
    
    # Format messages and invoke the LLM
    formatted_messages = prompt.format_messages(messages=messages)
    response = llm_with_tools.invoke(formatted_messages)
    
    # Return the response
    return {"messages": [response]}

# Fix the graph creation to handle config parameter
def create_graph():
    """Create and configure the agent graph"""
    graph = StateGraph(AgentState)

    # Create a custom tool execution node that handles the config parameter
    # and performs tracking directly.
    def custom_tool_node(state):
        if "messages" not in state or not state["messages"]:
            return {"messages": []}

        ai_message = None
        for message in reversed(state["messages"]):
            if isinstance(message, AIMessage) and hasattr(message, "tool_calls") and message.tool_calls:
                ai_message = message
                break
        
        if not ai_message or not hasattr(ai_message, "tool_calls") or not ai_message.tool_calls:
            # This can happen if the LLM decides not to call a tool, or if the state is malformed.
            # Returning an empty list of messages is usually appropriate here.
            logger.info("No tool calls found in the latest AI message.")
            return {"messages": []}

        result_messages = []
        for tool_call in ai_message.tool_calls: # ai_message.tool_calls is a list of ToolCall objects/dicts
            # Ensure we get the tool_call_id directly from the LLM's tool_call object/dict
            tool_call_id = tool_call.get('id') if isinstance(tool_call, dict) else getattr(tool_call, 'id', None)
            if not tool_call_id:
                # This should ideally not happen if the LLM is forming tool calls correctly.
                logger.error("Tool call from LLM is missing an ID. Generating a new one, but this may cause issues.")
                tool_call_id = str(uuid.uuid4())

            tool_name = tool_call.get('name') if isinstance(tool_call, dict) else getattr(tool_call, 'name', None)
            tool_args = tool_call.get('args') if isinstance(tool_call, dict) else getattr(tool_call, 'args', {})

            if not tool_name:
                logger.error(f"Tool call is missing a name. ID: {tool_call_id}")
                result_messages.append(
                    ToolMessage(content=f"Error: Tool call missing name.", tool_call_id=tool_call_id)
                )
                continue

            # Find the original tool from the global `tools` list
            matching_tool = None
            for t in tools: # Use the global `tools` list
                if t and t.name == tool_name:
                    matching_tool = t
                    break

            if not matching_tool:
                error_msg = f"Tool '{tool_name}' not found."
                logger.error(error_msg)
                result_messages.append(
                    ToolMessage(content=f"Error: {error_msg}", tool_call_id=tool_call_id)
                )
                continue

            # Start tracking
            logger.info(f"Executing tool '{tool_name}' (ID: {tool_call_id}) with args: {tool_args}")
            tool_tracking_id = add_tool_usage(tool_name, tool_args)

            try:
                # --> Add specific logging for RAG tool input <--
                if tool_name == "query_internal_documents":
                    query_text = tool_args.get('query', '[Query not found in args]')
                    logger.info(f"<<< RAG TOOL CALL >>> Querying retriever with: '{query_text}'")

                result = matching_tool.invoke(tool_args)

                # --> Add specific logging for RAG tool output <--
                if tool_name == "query_internal_documents":
                    # Log the raw result (which should be a list of Documents)
                    logger.info(f"<<< RAG TOOL RAW RESULT >>> Retriever returned: {result}")
                    # Also log the number of documents returned
                    num_docs = len(result) if isinstance(result, list) else "N/A (Result not a list)"
                    logger.info(f"<<< RAG TOOL RAW RESULT >>> Number of documents: {num_docs}")

                logger.info(f"Tool '{tool_name}' (ID: {tool_call_id}) completed successfully.")
                add_tool_usage(tool_name, tool_args, result, tool_tracking_id) # Update tracking with result
                try:
                    result_content = json.dumps(result)
                except TypeError:
                    logger.warning(f"Result from tool '{tool_name}' (ID: {tool_call_id}) is not JSON serializable. Converting to string.")
                    result_content = str(result)

            except Exception as e:
                logger.error(f"Error executing tool '{tool_name}' (ID: {tool_call_id}): {e}", exc_info=True)
                error_msg = f"Error: Tool '{tool_name}' failed with: {e}"
                add_tool_usage(tool_name, tool_args, {"error": str(e)}, tool_tracking_id) # Update tracking with error
                result_content = error_msg

            result_messages.append(
                ToolMessage(content=result_content, tool_call_id=tool_call_id) # Crucially, use the original tool_call_id from the LLM
            )

        return {"messages": result_messages}

    # Define the nodes in the graph
    graph.add_node("chatbot", chatbot)
    graph.add_node("tools", custom_tool_node)

    # Connect the nodes
    graph.add_conditional_edges(
        "chatbot",
        lambda x: "tools" if any(
            isinstance(msg, AIMessage) and hasattr(msg, "tool_calls") and msg.tool_calls
            for msg in x["messages"][-1:]
        ) else END,
    )
    graph.add_edge("tools", "chatbot")
    
    # Set the entry point
    graph.set_entry_point("chatbot")

    # Compile the graph
    app = graph.compile()
    return app

# Create the agent application
agent_app = create_graph()

# Add a timeout decorator
def timeout_handler(timeout_seconds=30):
    """Decorator to add timeout to a function"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            import signal
            
            def timeout_signal_handler(signum, frame):
                raise TimeoutError(f"Function timed out after {timeout_seconds} seconds")
            
            # Set the timeout handler
            original_handler = signal.signal(signal.SIGALRM, timeout_signal_handler)
            signal.alarm(timeout_seconds)
            
            try:
                result = func(*args, **kwargs)
                return result
            except TimeoutError as e:
                # Create a friendly timeout response
                query = args[0] if args else kwargs.get('query', 'Unknown query')
                return {
                    "response": "I'm sorry, but it took too long to process your request. Please try again or simplify your query.",
                    "debug": {
                        "tool_usage": [],
                        "message_count": 0,
                        "error": "Request timed out after {} seconds".format(timeout_seconds)
                    },
                    "trace_data": None
                }
            finally:
                # Reset the alarm and restore the original handler
                signal.alarm(0)
                signal.signal(signal.SIGALRM, original_handler)
        
        return wrapper
    return decorator

# Apply timeout to the get_agent_response function
# @timeout_handler(timeout_seconds=25) # Timeout decorator might need adjustment for async generators
async def get_agent_response(query: str) -> AsyncIterator[Dict[str, Any]]: # Changed to async generator
    """
    Get a response from the agent for a given query using LangGraph, streaming intermediate steps.
    
    Args:
        query: The user's question
        
    Yields:
        Dictionaries representing agent events or final response parts.
    """
    try:
        reset_tracker()
        initial_state = AgentState(messages=[HumanMessage(content=query)])
        
        logger.info(f"Agent starting stream for query: {query}")
        
        # Stream events from the LangGraph application
        # We are using version="v1" for astart_events for a more structured output
        async for event in agent_app.astream_events(initial_state, version="v1"):
            event_type = event["event"]
            # For now, just print the event to understand its structure
            # In the future, we will transform this into specific yields for the frontend
            logger.info(f"Agent event: {event_type}, Data: {event['data']}")
            
            # Example of what we might yield later (STRUCTURE IS PLACEHOLDER):
            # if event_type == "on_llm_start":
            #     yield {"type": "llm_start", "data": event["data"]}
            # elif event_type == "on_llm_stream":
            #     yield {"type": "llm_chunk", "data": event["data"]["chunk"]}
            # elif event_type == "on_tool_start":
            #     yield {"type": "tool_start", "name": event["data"]["name"], "input": event["data"]["input"]}
            # elif event_type == "on_tool_end":
            #     yield {"type": "tool_end", "name": event["data"]["name"], "output": event["data"]["output"]}
            # etc.

            # For this step, we just yield the raw event to see it in main.py
            yield event # YIELDING RAW EVENT FOR INSPECTION

        # After the loop, assemble final pieces if necessary (this part will change)
        # For now, this function will just yield events. 
        # The logic for constructing a final AgentLogicResponse equivalent will be handled by the caller (main.py)
        # or be part of the streamed events.
        logger.info("Agent stream finished.")

    except Exception as e:
        logger.error(f"Error in get_agent_response stream: {str(e)}", exc_info=True)
        yield {"type": "error", "data": {"error": str(e)}} # Yield an error event

# At the end of the file, re-create the agent app to ensure it uses the latest definitions
agent_app = create_graph() 