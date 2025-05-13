import pandas as pd
from datetime import datetime, timedelta
from langchain_core.tools import tool
import os
from typing import List, Dict, Optional, Union, Any

from .tool_logger import tool_logger

# Path to data files
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

def _load_data(file_name: str) -> pd.DataFrame:
    """Helper function to load CSV data"""
    file_path = os.path.join(DATA_DIR, file_name)
    print(f"Loading data from {file_path}")
    if not os.path.exists(file_path):
        print(f"WARNING: Data file {file_path} not found!")
        raise FileNotFoundError(f"Data file {file_path} not found. Make sure to run data_generator.py first.")
    return pd.read_csv(file_path)

# Original raw functions without decorators for direct use in agent.py
def _get_product_info(product_id: str) -> Dict[str, Any]:
    """
    Get information about a specific product by its product_id.
    
    Args:
        product_id: The product ID to look up (e.g., 'P123')
        
    Returns:
        Dictionary with product information
    """
    products_df = _load_data("products.csv")
    product = products_df[products_df['product_id'] == product_id]
    
    if product.empty:
        return {"error": f"Product with ID {product_id} not found"}
    
    return product.iloc[0].to_dict()

def _list_products(category: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """
    List products, optionally filtered by category.
    
    Args:
        category: Optional category to filter by (e.g., 'Apparel', 'Electronics')
        limit: Maximum number of products to return (default: 10)
        
    Returns:
        List of product dictionaries
    """
    products_df = _load_data("products.csv")
    
    if category:
        filtered_df = products_df[products_df['category'] == category]
    else:
        filtered_df = products_df
    
    return filtered_df.head(limit).to_dict('records')

def _get_inventory_level(product_id: str) -> Dict[str, Any]:
    """
    Get current inventory level for a specific product.
    
    Args:
        product_id: The product ID to look up (e.g., 'P123')
        
    Returns:
        Dictionary with inventory information
    """
    inventory_df = _load_data("inventory.csv")
    inventory = inventory_df[inventory_df['product_id'] == product_id]
    
    if inventory.empty:
        return {"error": f"Inventory for product ID {product_id} not found"}
    
    return inventory.iloc[0].to_dict()

def _list_low_stock_products(threshold: int = 10) -> List[Dict[str, Any]]:
    """
    List all products with inventory levels below the specified threshold.
    
    Args:
        threshold: Inventory quantity threshold (default: 10)
        
    Returns:
        List of product dictionaries with low inventory
    """
    inventory_df = _load_data("inventory.csv")
    products_df = _load_data("products.csv")
    
    # Find products with inventory below threshold
    low_stock = inventory_df[inventory_df['quantity'] < threshold]
    
    if low_stock.empty:
        return []
    
    # Join with product data
    result = pd.merge(low_stock, products_df, on='product_id')
    return result.to_dict('records')

def _get_sales_data_for_product(product_id: str, days: int = 30) -> Dict[str, Any]:
    """
    Get sales data for a specific product over the specified number of days.
    
    Args:
        product_id: The product ID to look up (e.g., 'P123')
        days: Number of days to look back (default: 30)
        
    Returns:
        Dictionary with sales information
    """
    orders_df = _load_data("orders.csv")
    order_items_df = _load_data("order_items.csv")
    
    # Calculate the date threshold
    today = datetime.now()
    date_threshold = (today - timedelta(days=days)).strftime('%Y-%m-%d')
    
    # Filter orders by date
    recent_orders = orders_df[orders_df['order_date'] >= date_threshold]
    
    if recent_orders.empty:
        return {"error": f"No orders found in the last {days} days"}
    
    # Filter order items by product and join with recent orders
    items = order_items_df[order_items_df['product_id'] == product_id]
    if items.empty:
        return {"total_units_sold": 0, "total_revenue": 0.0, "avg_daily_units": 0.0, "message": f"No sales for product {product_id} in the last {days} days"}
    
    # Join with orders to get dates
    sales = pd.merge(items, recent_orders, on='order_id')
    
    if sales.empty:
        return {"total_units_sold": 0, "total_revenue": 0.0, "avg_daily_units": 0.0, "message": f"No sales for product {product_id} in the last {days} days"}
    
    # Calculate metrics
    total_units = sales['quantity'].sum()
    total_revenue = sales['item_total'].sum()
    avg_daily_units = total_units / days
    
    return {
        "product_id": product_id,
        "period_days": days,
        "total_units_sold": int(total_units),
        "total_revenue": float(total_revenue),
        "avg_daily_units": float(avg_daily_units),
        "num_orders": len(sales)
    }

def _estimate_days_of_stock_remaining(product_id: str, days_to_analyze: int = 30) -> Dict[str, Any]:
    """
    Estimate how many days of stock remain for a product based on recent sales velocity.
    
    Args:
        product_id: The product ID to analyze (e.g., 'P123')
        days_to_analyze: Number of days to analyze for sales velocity (default: 30)
        
    Returns:
        Dictionary with stock projection information
    """
    # Get current inventory
    inventory_data = _get_inventory_level(product_id)
    if "error" in inventory_data:
        return inventory_data
    
    current_stock = inventory_data['quantity']
    
    # Get sales velocity
    sales_data = _get_sales_data_for_product(product_id, days=days_to_analyze)
    if "error" in sales_data:
        return {"error": sales_data["error"]}
    
    if sales_data.get("total_units_sold", 0) == 0:
        return {
            "product_id": product_id,
            "current_stock": current_stock,
            "avg_daily_units_sold": 0,
            "days_remaining": "Infinite (no recent sales)",
            "stock_status": "Overstocked"
        }
    
    # Calculate days remaining
    avg_daily_units = sales_data["avg_daily_units"]
    
    if avg_daily_units <= 0:
        days_remaining = float('inf')
        days_remaining_str = "Infinite (no sales velocity)"
        stock_status = "Overstocked"
    else:
        days_remaining = current_stock / avg_daily_units
        days_remaining_str = f"{round(days_remaining, 1)} days"
        
        # Determine stock status
        if days_remaining < 7:
            stock_status = "Critical - Reorder immediately"
        elif days_remaining < 14:
            stock_status = "Low - Reorder soon"
        elif days_remaining < 30:
            stock_status = "Adequate"
        elif days_remaining < 60:
            stock_status = "Healthy"
        else:
            stock_status = "Overstocked"
    
    return {
        "product_id": product_id,
        "current_stock": current_stock,
        "avg_daily_units_sold": float(avg_daily_units),
        "days_remaining": days_remaining_str,
        "stock_status": stock_status
    }

def _get_top_selling_products(days: int = 30, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Get the top selling products by quantity over the specified time period.
    
    Args:
        days: Number of days to look back (default: 30)
        limit: Number of top products to return (default: 5)
        
    Returns:
        List of dictionaries with top selling products and their sales data
    """
    try:
        orders_df = _load_data("orders.csv")
        order_items_df = _load_data("order_items.csv")
        products_df = _load_data("products.csv")
        
        # Calculate the date threshold
        today = datetime.now()
        date_threshold = (today - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # Filter orders by date
        recent_orders = orders_df[orders_df['order_date'] >= date_threshold]
        
        if recent_orders.empty:
            return []
        
        # Join order items with recent orders
        sales = pd.merge(order_items_df, recent_orders, on='order_id')
        
        if sales.empty:
            return []
        
        # Group by product and sum quantities
        product_sales = sales.groupby('product_id').agg({
            'quantity': 'sum',
            'item_total': 'sum'
        }).reset_index()
        
        # Sort by quantity sold, descending
        top_products = product_sales.sort_values('quantity', ascending=False).head(limit)
        
        # Join with product info
        result = pd.merge(top_products, products_df, on='product_id')
        
        return result.to_dict('records')
    except Exception as e:
        # Return error information instead of raising exception
        return [{"error": f"Error fetching top products: {str(e)}"}]

# Update the tool decorators to handle config correctly
@tool
@tool_logger
def get_product_info(product_id: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Get information about a specific product by its product_id.
    
    Args:
        product_id: The product ID to look up (e.g., 'P123')
        config: Optional configuration for the tool
        
    Returns:
        Dictionary with product information
    """
    return _get_product_info(product_id)

@tool
@tool_logger
def list_products(category: Optional[str] = None, limit: int = 10, config: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    List products, optionally filtered by category.
    
    Args:
        category: Optional category to filter by (e.g., 'Apparel', 'Electronics')
        limit: Maximum number of products to return (default: 10)
        config: Optional configuration for the tool
        
    Returns:
        List of product dictionaries
    """
    return _list_products(category, limit)

@tool
@tool_logger
def get_inventory_level(product_id: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Get current inventory level for a specific product.
    
    Args:
        product_id: The product ID to look up (e.g., 'P123')
        config: Optional configuration for the tool
        
    Returns:
        Dictionary with inventory information
    """
    return _get_inventory_level(product_id)

@tool
@tool_logger
def list_low_stock_products(threshold: int = 10, config: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    List all products with inventory levels below the specified threshold.
    
    Args:
        threshold: Inventory quantity threshold (default: 10)
        config: Optional configuration for the tool
        
    Returns:
        List of product dictionaries with low inventory
    """
    return _list_low_stock_products(threshold)

@tool
@tool_logger
def get_sales_data_for_product(product_id: str, days: int = 30, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Get sales data for a specific product over the specified number of days.
    
    Args:
        product_id: The product ID to look up (e.g., 'P123')
        days: Number of days to look back (default: 30)
        config: Optional configuration for the tool
        
    Returns:
        Dictionary with sales information
    """
    return _get_sales_data_for_product(product_id, days)

@tool
@tool_logger
def estimate_days_of_stock_remaining(product_id: str, days_to_analyze: int = 30, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Estimate how many days of stock remain for a product based on recent sales velocity.
    
    Args:
        product_id: The product ID to analyze (e.g., 'P123')
        days_to_analyze: Number of days to analyze for sales velocity (default: 30)
        config: Optional configuration for the tool
        
    Returns:
        Dictionary with stock projection information
    """
    return _estimate_days_of_stock_remaining(product_id, days_to_analyze)

@tool
@tool_logger
def get_top_selling_products(days: int = 30, limit: int = 5, config: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Get the top selling products by quantity over the specified time period.
    
    Args:
        days: Number of days to look back (default: 30)
        limit: Number of top products to return (default: 5)
        config: Optional configuration for the tool
        
    Returns:
        List of dictionaries with top selling products and their sales data
    """
    return _get_top_selling_products(days, limit) 