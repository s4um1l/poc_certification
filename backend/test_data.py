"""
Test script to verify data loading functionality
"""
import os
import sys
from app.tools import _load_data, DATA_DIR

def main():
    """Test loading data files"""
    print(f"DATA_DIR = {DATA_DIR}")
    print(f"Working directory: {os.getcwd()}")
    
    # Check if data directory exists
    if os.path.exists(DATA_DIR):
        print(f"Data directory exists: {DATA_DIR}")
        # List all files in data directory
        files = os.listdir(DATA_DIR)
        print(f"Files in data directory: {files}")
    else:
        print(f"ERROR: Data directory does not exist: {DATA_DIR}")
        return
    
    # Try loading each data file
    data_files = ["products.csv", "inventory.csv", "orders.csv", "order_items.csv"]
    for file_name in data_files:
        try:
            data = _load_data(file_name)
            print(f"Successfully loaded {len(data)} records from {file_name}")
        except Exception as e:
            print(f"Error loading {file_name}: {e}")

if __name__ == "__main__":
    main() 