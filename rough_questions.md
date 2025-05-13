
Based on the tools in your agent, here are some powerful queries that would use multiple tools:

1. **"Which of my top-selling products are at risk of running out of stock soon?"**
   - This would use:
     - `get_top_selling_products` to identify best sellers
     - `get_inventory_level` to check current stock
     - `estimate_days_of_stock_remaining` to predict when they'll run out

2. **"For products in the Electronics category, show me inventory levels and recent sales performance"**
   - This would use:
     - `list_products` with category filter
     - `get_inventory_level` for each product
     - `get_sales_data_for_product` for sales metrics

3. **"Which low inventory products should I prioritize restocking based on sales velocity?"**
   - This would use:
     - `list_low_stock_products` to find low inventory items
     - `get_sales_data_for_product` for each to analyze velocity
     - `estimate_days_of_stock_remaining` to determine urgency

4. **"Compare the sales and inventory status of my top 3 selling Apparel products"**
   - This would use:
     - `list_products` to find Apparel items
     - `get_top_selling_products` to identify best performers
     - `get_inventory_level` for current stock
     - `get_sales_data_for_product` for detailed sales analysis

5. **"What's my overall inventory health - show me products with critical stock levels and their sales performance"**
   - This would use:
     - `list_low_stock_products` 
     - `get_sales_data_for_product` for each low stock item
     - `estimate_days_of_stock_remaining` to determine critical items

These queries showcase the agent's ability to combine different data sources and provide sophisticated business intelligence.
