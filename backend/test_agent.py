"""
Test a simpler version of our agent
"""
import json
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from app.tools import (
    get_product_info,
    list_products,
    get_inventory_level,
    list_low_stock_products,
    get_sales_data_for_product,
    estimate_days_of_stock_remaining,
    get_top_selling_products
)

def test_agent():
    """Test a simple version of the agent with direct LLM tool calling"""
    # Load API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable not set")
        return
    
    # Set up the model
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    # Bind tools to the model
    tools = [
        get_product_info,
        list_products,
        get_inventory_level,
        list_low_stock_products,
        get_sales_data_for_product,
        estimate_days_of_stock_remaining,
        get_top_selling_products
    ]
    llm_with_tools = llm.bind_tools(tools)
    
    # Create a system prompt
    system_prompt = """
    You are an AI Shopping Operations Assistant for a Shopify merchant. Your job is to help the merchant understand their sales velocity and inventory levels.
    
    You analyze sales and inventory data to provide insights and answer operational questions.
    
    Always follow these guidelines:
    1. Use the tools to answer questions accurately. Don't make up information.
    2. If you need specific product IDs or time periods that weren't provided, ask for clarification.
    3. Be precise and concise in your responses.
    4. Format numbers clearly (e.g., use $ for dollar amounts, % for percentages).
    5. Provide actionable insights where possible (e.g., note if inventory is critically low).
    
    Important: You must use tools to retrieve data before answering questions about inventory or sales.
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{query}")
    ])
    
    # Test queries
    queries = [
        "Which products have less than 5 units in stock?",
        "What are the top 3 selling products?",
        "What is the inventory level for product P301?"
    ]
    
    for query in queries:
        print(f"\n=== Testing query: {query} ===")
        formatted_prompt = prompt.format_messages(query=query)
        response = llm_with_tools.invoke(formatted_prompt)
        print(response.content)
        
        # Also print out tool usage if possible
        if hasattr(response, "tool_calls") and response.tool_calls:
            print("\nTool calls:")
            for tc in response.tool_calls:
                print(f"- {tc.name}({tc.args})")

if __name__ == "__main__":
    test_agent() 