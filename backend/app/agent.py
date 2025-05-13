import os
import uuid
from typing import List, Dict, Any, Sequence, TypedDict, Callable, Optional
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

# Create instrumented tool wrappers that will track usage
def create_instrumented_tool(original_tool):
    """Create an instrumented version of a tool that tracks usage"""
    wrapped_tool = copy.deepcopy(original_tool)
    original_func = wrapped_tool._run
    
    def instrumented_run(*args, **kwargs):
        input_data = kwargs.copy()
        if 'config' in input_data:
            # Don't include config in the tracked data
            input_data.pop('config')
            
        # Record the start of the tool call
        tool_id = add_tool_usage(wrapped_tool.name, input_data)
        try:
            # Run the original tool with all params including config
            result = original_func(*args, **kwargs)
            # Update with the result
            add_tool_usage(wrapped_tool.name, input_data, result, tool_id)
            return result
        except Exception as e:
            # Log the error
            add_tool_usage(wrapped_tool.name, input_data, {"error": str(e)}, tool_id)
            raise
            
    wrapped_tool._run = instrumented_run
    return wrapped_tool

# Instrument all tools for better tracking
instrumented_tools = [create_instrumented_tool(t) for t in [
    get_product_info,
    list_products,
    get_inventory_level,
    list_low_stock_products,
    get_sales_data_for_product,
    estimate_days_of_stock_remaining,
    get_top_selling_products
]]

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

# Define the tools
tools = instrumented_tools

# System prompt template
SYSTEM_PROMPT = """
You are an AI Shopping Operations Assistant for a Shopify merchant. Your job is to help the merchant understand their sales velocity and inventory levels.

You analyze sales and inventory data to provide insights and answer operational questions.

You have access to the following tools:

{tool_descriptions}

Always follow these guidelines:
1. Use the tools to answer questions accurately. Don't make up information.
2. If you need specific product IDs or time periods that weren't provided, ask for clarification.
3. Be precise and concise in your responses.
4. Format numbers clearly (e.g., use $ for dollar amounts, % for percentages).
5. Provide actionable insights where possible (e.g., note if inventory is critically low).

Important: You must use tools to retrieve data before answering questions about inventory or sales.
"""

# Define the chatbot function using LLM with tools
def chatbot(state: AgentState):
    """Process the messages using the LLM"""
    # Get the LLM
    llm = get_llm()
    
    # Bind the tools to the LLM
    llm_with_tools = llm.bind_tools(tools)
    
    # Create prompt template with system message
    tool_descriptions = "\n".join([f"- {tool.name}: {tool.description}" for tool in tools])
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
    # Define the workflow
    graph = StateGraph(AgentState)
    
    # Create a custom tool execution node that handles the config parameter
    def custom_tool_node(state):
        # Extract the latest AI message to get the tool calls
        if "messages" not in state or not state["messages"]:
            return {"messages": []}
            
        ai_message = None
        for message in reversed(state["messages"]):
            if isinstance(message, AIMessage) and hasattr(message, "tool_calls") and message.tool_calls:
                ai_message = message
                break
        
        if not ai_message or not hasattr(ai_message, "tool_calls") or not ai_message.tool_calls:
            return {"messages": []}
        
        result_messages = []
        for tool_call in ai_message.tool_calls:
            try:
                # Get the tool by name
                tool_name = tool_call.name if hasattr(tool_call, "name") else tool_call.get("name")
                tool_args = tool_call.args if hasattr(tool_call, "args") else tool_call.get("args", {})
                
                # Add the config parameter
                tool_args["config"] = {}
                
                # Find the matching tool
                matching_tool = None
                for tool in tools:
                    if tool.name == tool_name:
                        matching_tool = tool
                        break
                
                if not matching_tool:
                    error_msg = f"Tool {tool_name} not found"
                    # Create tool message with a valid tool_call_id
                    # Ensure we're getting a proper tool_call_id by checking various attributes
                    tool_call_id = None
                    if hasattr(tool_call, "id"):
                        tool_call_id = tool_call.id
                    elif isinstance(tool_call, dict) and "id" in tool_call:
                        tool_call_id = tool_call["id"]
                    # If we can't find an id, generate a new UUID
                    if not tool_call_id:
                        tool_call_id = str(uuid.uuid4())
                        
                    result_messages.append(
                        ToolMessage(content=f"Error: {error_msg}", tool_call_id=tool_call_id)
                    )
                    continue
                
                # Execute the tool with config
                try:
                    result = matching_tool.invoke(tool_args)
                except AttributeError:
                    # Fall back to older __call__ method if invoke is not available
                    result = matching_tool(**tool_args)
                
                # Create a result message with a valid tool_call_id
                # Ensure we're getting a proper tool_call_id by checking various attributes
                tool_call_id = None
                if hasattr(tool_call, "id"):
                    tool_call_id = tool_call.id
                elif isinstance(tool_call, dict) and "id" in tool_call:
                    tool_call_id = tool_call["id"]
                # If we can't find an id, generate a new UUID
                if not tool_call_id:
                    tool_call_id = str(uuid.uuid4())
                    
                result_messages.append(
                    ToolMessage(content=json.dumps(result), tool_call_id=tool_call_id)
                )
                
            except Exception as e:
                # Handle errors
                error_msg = f"Error executing tool {tool_call.name if hasattr(tool_call, 'name') else 'unknown'}: {str(e)}"
                # Create tool message with a valid tool_call_id
                # Ensure we're getting a proper tool_call_id by checking various attributes
                tool_call_id = None
                if hasattr(tool_call, "id"):
                    tool_call_id = tool_call.id
                elif isinstance(tool_call, dict) and "id" in tool_call:
                    tool_call_id = tool_call["id"]
                # If we can't find an id, generate a new UUID
                if not tool_call_id:
                    tool_call_id = str(uuid.uuid4())
                    
                result_messages.append(
                    ToolMessage(content=f"Error: {error_msg}", tool_call_id=tool_call_id)
                )
        
        return {"messages": result_messages}
    
    # Define the nodes in the graph
    graph.add_node("chatbot", chatbot)
    graph.add_node("tools", custom_tool_node)
    
    # Connect the nodes - modified for custom tool node
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
@timeout_handler(timeout_seconds=25)
def get_agent_response(query: str) -> Dict[str, Any]:
    """
    Get a response from the agent for a given query using LangGraph.
    
    Args:
        query: The user's question
        
    Returns:
        Dictionary with response and debug information
    """
    try:
        # Reset tool usage tracker for the new query
        reset_tracker()
        
        # Prepare the initial state for the graph
        initial_state = AgentState(messages=[HumanMessage(content=query)])
        
        # Invoke the LangGraph application
        # Note: We might need to handle streaming or config if needed later
        final_state = agent_app.invoke(initial_state)
        
        # Extract the final response message
        final_response_message = final_state['messages'][-1]
        response_content = ""
        if isinstance(final_response_message, AIMessage):
            response_content = final_response_message.content
        elif isinstance(final_response_message, dict) and 'content' in final_response_message:
            # Handle potential dictionary format if invoke changes behavior
            response_content = final_response_message['content']
        else:
            # Fallback if the last message isn't the expected AI response
            response_content = "Could not extract a final response from the agent."

        # Extract tool usage from the tracker
        tracked_usage = get_tool_usage()

        return {
            "response": response_content,
            "debug": {
                "tool_usage": tracked_usage,
                "message_count": len(final_state.get("messages", [])), # Count messages in the final state
                "error": None # Clear previous error if successful
            },
            "trace_data": None # Placeholder for potential tracing integration
        }
    
    except TimeoutError as te:
        # Handle specific timeout error from decorator
        print(f"TimeoutError in get_agent_response: {str(te)}")
        tracked_usage = get_tool_usage() # Get usage even on timeout
        return {
            "response": "I'm sorry, but it took too long to process your request. Please try again or simplify your query.",
            "debug": {
                "tool_usage": tracked_usage,
                "message_count": 0, # No final state available
                "error": str(te)
            },
            "trace_data": None
        }
    except Exception as e:
        print(f"Error in get_agent_response: {str(e)}")
        tracked_usage = get_tool_usage() # Get usage even on other errors
        return {
            "response": f"I'm sorry, but there was an error processing your request. Please try again.",
            "debug": {
                "tool_usage": tracked_usage,
                "message_count": 0, # No final state available
                "error": str(e)
            },
            "trace_data": None
        }

# At the end of the file, after all definitions, re-create the agent app
# Create the agent application
agent_app = create_graph()  # Re-create with our updated implementation 