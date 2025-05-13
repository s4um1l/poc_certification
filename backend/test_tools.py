"""
Test the tool functions directly
"""
import json
from app.tools import (
    _list_low_stock_products,
    _get_product_info,
    _list_products,
    _get_inventory_level,
    _get_sales_data_for_product,
    _estimate_days_of_stock_remaining,
    _get_top_selling_products
)

def test_low_stock_products():
    """Test the low stock products function"""
    print("\n=== Testing list_low_stock_products ===")
    result = _list_low_stock_products(threshold=10)
    print(f"Found {len(result)} products with stock below 10")
    if result:
        print("First few results:")
        for item in result[:3]:
            print(json.dumps(item, indent=2))
    else:
        print("No low stock products found")
    
    # Try with a higher threshold
    result = _list_low_stock_products(threshold=20)
    print(f"\nFound {len(result)} products with stock below 20")
    
def test_product_info():
    """Test the product info function"""
    print("\n=== Testing get_product_info ===")
    # Get a valid product ID from products list
    products = _list_products(limit=1)
    if products:
        product_id = products[0]["product_id"]
        print(f"Looking up product: {product_id}")
        result = _get_product_info(product_id)
        print(json.dumps(result, indent=2))
    else:
        print("No products found to test with")

def test_inventory_level():
    """Test the inventory level function"""
    print("\n=== Testing get_inventory_level ===")
    # Get a valid product ID from products list
    products = _list_products(limit=1)
    if products:
        product_id = products[0]["product_id"]
        print(f"Looking up inventory for: {product_id}")
        result = _get_inventory_level(product_id)
        print(json.dumps(result, indent=2))
    else:
        print("No products found to test with")

def test_sales_data():
    """Test the sales data function"""
    print("\n=== Testing get_sales_data_for_product ===")
    # Get a valid product ID from products list
    products = _list_products(limit=1)
    if products:
        product_id = products[0]["product_id"]
        print(f"Looking up sales data for: {product_id}")
        result = _get_sales_data_for_product(product_id)
        print(json.dumps(result, indent=2))
    else:
        print("No products found to test with")

def test_top_selling():
    """Test the top selling products function"""
    print("\n=== Testing get_top_selling_products ===")
    result = _get_top_selling_products(limit=3)
    print(f"Found {len(result)} top selling products")
    if result:
        print("Results:")
        for item in result:
            print(json.dumps(item, indent=2))
    else:
        print("No top selling products found")

def main():
    """Run all the tool tests"""
    test_low_stock_products()
    test_product_info()
    test_inventory_level()
    test_sales_data()
    test_top_selling()

if __name__ == "__main__":
    main() 