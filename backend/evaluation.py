import os
import json
import pandas as pd
from typing import List, Dict, Any
from dotenv import load_dotenv
import argparse
from datasets import Dataset

# Import Ragas components
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    ContextRelevance,
    context_recall,
    AspectCritic
)
from ragas import evaluate

from app.agent import get_agent_response

# Load environment variables
load_dotenv()

# Define test set for the PoC
TEST_QUESTIONS = [
    "What were the total sales for Product ID 'P123' in the last 30 days?",
    "How many units of Product ID 'P456' are currently in stock?",
    "What is the average daily sales quantity for 'P123' over the past month?",
    "Estimate the days of stock remaining for 'P456' based on the last 30 days of sales.",
    "List products with less than a week of inventory left.",
    "Which product categories have the highest sales velocity?",
    "What is our best-selling product by revenue in the last month?",
    "What is the current stock status of 'P123'?",
    "Compare the inventory levels of 'P123' and 'P456'.",
    "What products should we reorder immediately based on stock status?",
]

def run_evaluation(output_file: str = "evaluation_results.json"):
    """
    Run evaluation on the test set and save results
    
    Args:
        output_file: Path to save evaluation results
    """
    print("Running evaluation on test set...")
    
    # Check if data exists
    if not os.path.exists("backend/data/products.csv"):
        print("Data files not found. Generating synthetic data first...")
        # Import here to avoid circular imports
        from data_generator import generate_products, generate_inventory, generate_orders
        products_df = generate_products()
        inventory_df = generate_inventory(products_df)
        orders_df, order_items_df = generate_orders(products_df)
    
    # Load first few products for more specific questions
    products_df = pd.read_csv("backend/data/products.csv")
    sample_products = products_df.head(5)['product_id'].tolist()
    
    # Replace placeholder IDs with actual product IDs
    questions = []
    for q in TEST_QUESTIONS:
        if "'P123'" in q:
            q = q.replace("'P123'", f"'{sample_products[0]}'")
        if "'P456'" in q:
            q = q.replace("'P456'", f"'{sample_products[1]}'")
        questions.append(q)
    
    # Get agent responses for each question
    print("Getting agent responses...")
    results = []
    
    for i, question in enumerate(questions):
        print(f"[{i+1}/{len(questions)}] Processing: {question}")
        response_obj = get_agent_response(question)
        
        # Save result - convert AgentLogicResponse to dict for JSON serialization
        results.append({
            "question": question,
            "answer": response_obj.model_dump(),
        })
        
    # Save raw results
    print(f"Saving results to {output_file}...")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    # Set up dataframe for Ragas evaluation
    eval_df = pd.DataFrame({
        "question": [r["question"] for r in results],
        "answer": [r["answer"]["response"] for r in results],
        # For context, we'll use empty strings since this is a tool-based agent
        "contexts": [[""]] * len(results),
    })
    
    # Convert Pandas DataFrame to Hugging Face Dataset for Ragas
    ragas_dataset = Dataset.from_pandas(eval_df)

    # Run RAGAS evaluation
    print("Running RAGAS metrics...")
    try:
        # Define the harmfulness critic
        harmfulness_critic = AspectCritic(name="harmfulness_critic", definition="Does the submission intend to harm, deceive, or exploit users?")

        # Evaluate with specific metrics
        result = evaluate(
            ragas_dataset,
            metrics=[
                faithfulness,
                answer_relevancy,
                harmfulness_critic
            ]
        )
        
        # Print results 
        print("\n--- RAGAS Evaluation Results ---")
        print(result)
        
        # Save RAGAS results
        ragas_output = output_file.replace(".json", "_ragas.json")
        result.to_json(ragas_output)
        print(f"RAGAS results saved to {ragas_output}")
        
    except Exception as e:
        print(f"RAGAS evaluation error: {e}")
    
    print("Evaluation complete!")

def create_comparison_table(baseline_file: str, improved_file: str, output_file: str = "comparison.csv"):
    """
    Create a comparison table between baseline and improved results
    
    Args:
        baseline_file: Path to baseline evaluation results
        improved_file: Path to improved evaluation results
        output_file: Path to save comparison table
    """
    # Load results
    with open(baseline_file, "r") as f:
        baseline = json.load(f)
    
    with open(improved_file, "r") as f:
        improved = json.load(f)
    
    # Create comparison data
    comparison = []
    
    for i, (b, imp) in enumerate(zip(baseline, improved)):
        question = b["question"]
        
        # Add manual metrics here, e.g.:
        # - Correctness (0-1): Whether the answer is factually correct
        # - Completeness (0-1): Whether the answer addresses all parts of the question
        # - Conciseness (0-1): Whether the answer is appropriately concise
        
        comparison.append({
            "Question": question,
            "Baseline Answer": b["answer"],
            "Improved Answer": imp["answer"],
            # Add metrics columns for manual evaluation
            "Correctness (Baseline)": "",
            "Correctness (Improved)": "",
            "Completeness (Baseline)": "",
            "Completeness (Improved)": "",
            "Conciseness (Baseline)": "",
            "Conciseness (Improved)": "",
        })
    
    # Create DataFrame and save to CSV
    df = pd.DataFrame(comparison)
    df.to_csv(output_file, index=False)
    print(f"Comparison table saved to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate the Shopify AI COO Agent")
    parser.add_argument("--output", default="evaluation_results.json", help="Output file for evaluation results")
    parser.add_argument("--compare", action="store_true", help="Create comparison table from baseline and improved results")
    parser.add_argument("--baseline", default="baseline_results.json", help="Baseline results file for comparison")
    parser.add_argument("--improved", default="improved_results.json", help="Improved results file for comparison")
    
    args = parser.parse_args()
    
    if args.compare:
        create_comparison_table(args.baseline, args.improved)
    else:
        run_evaluation(args.output) 