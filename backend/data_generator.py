import pandas as pd
import numpy as np
from faker import Faker
import os
import uuid
from datetime import datetime, timedelta

# Set up Faker
fake = Faker()

# Ensure data directory exists
os.makedirs('backend/data', exist_ok=True)

# Generate product data
def generate_products(num_products=50):
    """Generate synthetic product data"""
    products = []
    
    categories = ['Apparel', 'Electronics', 'Home Goods', 'Beauty', 'Accessories']
    
    for _ in range(num_products):
        product_id = f"P{fake.unique.random_int(min=100, max=999)}"
        product = {
            'product_id': product_id,
            'name': fake.unique.catch_phrase(),
            'category': fake.random_element(categories),
            'price': round(fake.random_number(digits=2) + fake.random.random(), 2),
            'cost': round(fake.random_number(digits=1) + fake.random.random(), 2),
            'created_at': fake.date_time_between(start_date='-1y', end_date='now').strftime('%Y-%m-%d')
        }
        products.append(product)
    
    df = pd.DataFrame(products)
    df.to_csv('backend/data/products.csv', index=False)
    return df

# Generate inventory data
def generate_inventory(products_df):
    """Generate synthetic inventory data based on products"""
    inventory = []
    
    for _, product in products_df.iterrows():
        inventory_item = {
            'product_id': product['product_id'],
            'quantity': fake.random_int(min=0, max=200),
            'warehouse': fake.random_element(['Main', 'East', 'West', 'North']),
            'last_updated': fake.date_time_between(start_date='-30d', end_date='now').strftime('%Y-%m-%d %H:%M:%S')
        }
        inventory.append(inventory_item)
    
    df = pd.DataFrame(inventory)
    df.to_csv('backend/data/inventory.csv', index=False)
    return df

# Generate order data
def generate_orders(products_df, num_orders=500):
    """Generate synthetic order data"""
    orders = []
    order_items = []
    
    # Generate orders over the last 90 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    for _ in range(num_orders):
        order_id = str(uuid.uuid4())[:8].upper()
        order_date = fake.date_time_between(start_date=start_date, end_date=end_date)
        
        # Basic order info
        order = {
            'order_id': order_id,
            'customer_id': f"C{fake.random_int(min=1000, max=9999)}",
            'order_date': order_date.strftime('%Y-%m-%d %H:%M:%S'),
            'total_amount': 0,  # Will be calculated
            'status': fake.random_element(['completed', 'shipped', 'processing', 'cancelled']),
            'payment_method': fake.random_element(['credit_card', 'paypal', 'apple_pay', 'shop_pay'])
        }
        
        # Generate 1-5 items per order
        num_items = fake.random_int(min=1, max=5)
        order_total = 0
        
        # Randomly select products for this order
        selected_products = products_df.sample(n=min(num_items, len(products_df)))
        
        for _, product in selected_products.iterrows():
            quantity = fake.random_int(min=1, max=3)
            item_total = quantity * product['price']
            order_total += item_total
            
            order_item = {
                'order_id': order_id,
                'product_id': product['product_id'],
                'quantity': quantity,
                'price_per_unit': product['price'],
                'item_total': item_total
            }
            order_items.append(order_item)
        
        # Update the order total
        order['total_amount'] = round(order_total, 2)
        orders.append(order)
    
    # Create DataFrames and save to CSV
    orders_df = pd.DataFrame(orders)
    orders_df.to_csv('backend/data/orders.csv', index=False)
    
    order_items_df = pd.DataFrame(order_items)
    order_items_df.to_csv('backend/data/order_items.csv', index=False)
    
    return orders_df, order_items_df

if __name__ == "__main__":
    print("Generating synthetic Shopify data...")
    products_df = generate_products()
    inventory_df = generate_inventory(products_df)
    orders_df, order_items_df = generate_orders(products_df)
    print("Data generation complete. Files saved to backend/data/ directory.")
    print(f"Generated {len(products_df)} products")
    print(f"Generated {len(inventory_df)} inventory records")
    print(f"Generated {len(orders_df)} orders")
    print(f"Generated {len(order_items_df)} order line items") 