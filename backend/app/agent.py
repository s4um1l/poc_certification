import os
from typing import List, Dict, Any, Sequence, Annotated, TypedDict
from dotenv import load_dotenv
from operator import add

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from .tools import (
    get_product_info,
    list_products,
    get_inventory_level,
    list_low_stock_products,
    get_sales_data_for_product,
    estimate_days_of_stock_remaining,
    get_top_selling_products
)

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

# Configure tools
tools = [
    get_product_info,
    list_products,
    get_inventory_level,
    list_low_stock_products,
    get_sales_data_for_product,
    estimate_days_of_stock_remaining,
    get_top_selling_products
]

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

# Create the graph
def create_graph():
    """Create and configure the agent graph"""
    # Define the workflow
    graph = StateGraph(AgentState)
    
    # Define the nodes in the graph
    graph.add_node("chatbot", chatbot)
    graph.add_node("tools", ToolNode(tools=tools))
    
    # Connect the nodes
    graph.add_conditional_edges(
        "chatbot",
        tools_condition,
    )
    graph.add_edge("tools", "chatbot")
    
    # Set the entry point
    graph.set_entry_point("chatbot")
    
    # Compile the graph
    app = graph.compile()
    
    return app

# Create the agent application
agent_app = create_graph()

# Function to get a response from the agent
def get_agent_response(query: str) -> str:
    """
    Get a response from the agent for a given query.
    
    Args:
        query: The user's question
        
    Returns:
        The agent's response as a string
    """
    # Create the initial state
    initial_state = {
        "messages": [HumanMessage(content=query)],
    }
    
    # Run the agent
    result = agent_app.invoke(initial_state)
    
    # Extract the response from the final AI message
    final_message = result["messages"][-1]
    
    # Return the content of the final message
    return final_message.content 