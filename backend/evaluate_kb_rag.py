import os
import pandas as pd
from dotenv import load_dotenv
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,  # Ragas uses this for response_relevancy
    context_precision,
    context_recall,
    answer_correctness # Added answer_correctness
)
from datasets import Dataset
import json
from tqdm.asyncio import tqdm # For async tqdm
import asyncio # Added for async operations
import glob # For finding testset files
import aiohttp # Added for async HTTP requests
from collections import UserDict # Added for type checking
from collections.abc import Mapping # Added for type checking

# Load environment variables at the very beginning
load_dotenv()

# Actual imports for the RAG functionality - REMOVED langchain and local RAG
# from backend.data_processing import setup_vector_store # Assuming relative import works from where script is run
# from langchain_openai import ChatOpenAI
# from langchain_core.prompts import ChatPromptTemplate

# Initialize LLM globally or pass as argument if preferred - REMOVED
# Ensure OPENAI_API_KEY is in .env
# llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

# Global retriever, initialized once - REMOVED
# retriever = None

# REMOVED initialize_retriever and initialize_retriever_sync_fallback functions

# Configuration for the API endpoint
API_RAG_TEST_URL = os.getenv("API_RAG_TEST_URL", "http://localhost:8000/api/test_rag") # Changed URL
# RAG_TOOL_NAME = "query_internal_documents" # No longer needed as we directly test RAG output

async def get_internal_docs_tool_response(query: str, session: aiohttp.ClientSession) -> dict:
    """
    Calls the backend API's /api/test_rag endpoint to get an answer and contexts.
    This endpoint directly tests the RAG retriever.
    """
    payload = {"query": query}
    # print(f"Calling API: {API_RAG_TEST_URL} with query: '{query}'")
    
    answer = f"Error: Could not retrieve RAG response for query: {query}"
    contexts = []

    try:
        async with session.post(API_RAG_TEST_URL, json=payload) as response:
            response.raise_for_status() 
            response_data = await response.json()
            # print(f"Received API response: {json.dumps(response_data, indent=2)}")

            retrieved_answer = response_data.get("answer")
            retrieved_contexts = response_data.get("contexts")

            if retrieved_answer is not None and retrieved_contexts is not None:
                answer = retrieved_answer
                contexts = retrieved_contexts
            else:
                print(f"Warning: API response from /api/test_rag for query '{query}' did not contain 'answer' or 'contexts'. Response: {response_data}")
                # Keep default error answer and empty contexts
            
            return {"answer": answer, "contexts": contexts}

    except aiohttp.ClientResponseError as e:
        print(f"API call to /api/test_rag failed for query '{query}': {e.message} (Status: {e.status})")
        error_body = "No response body"
        if response: # Check if response object exists before trying to read from it
            try:
                error_body = await response.text()
            except Exception as read_err:
                error_body = f"Could not read error response body: {read_err}"
        print(f"Error response body: {error_body}")
        answer = f"Error: API call to /api/test_rag failed with status {e.status}. {e.message}"
    except aiohttp.ClientError as e:
        print(f"API call to /api/test_rag failed (ClientError) for query '{query}': {e}")
        answer = f"Error: API call (ClientError) to /api/test_rag failed. {e}"
    except json.JSONDecodeError as e:
        print(f"Failed to decode JSON response from /api/test_rag for query '{query}': {e.msg}")
        raw_text = "Unknown (response object not available for raw text)"
        # Check if response object exists and has text method, typical in aiohttp
        if 'response' in locals() and hasattr(response, 'text'): 
            try:
                raw_text = await response.text()
            except Exception as read_err:
                raw_text = f"Could not read raw text from response: {read_err}"
        print(f"Raw response text: {raw_text}")
        answer = "Error: Could not decode API response from /api/test_rag."
    except Exception as e:
        print(f"An unexpected error occurred in get_internal_docs_tool_response (/api/test_rag) for query '{query}': {e}")
        answer = f"Error: An unexpected error occurred calling /api/test_rag. {e}"

    return {"answer": answer, "contexts": contexts}


async def run_evaluation_for_testset(testset_csv_path: str, results_output_dir: str, session: aiohttp.ClientSession):
    print(f"\n--- Running evaluation for testset: {testset_csv_path} ---")
    
    test_df = pd.read_csv(testset_csv_path)
    base_name = os.path.basename(testset_csv_path).replace(".csv", "")
    output_json_file = os.path.join(results_output_dir, f"ragas_eval_{base_name}.json")
    output_csv_file = os.path.join(results_output_dir, f"ragas_eval_{base_name}.csv")

    questions = []
    ground_truths = []
    answers = []
    retrieved_contexts_list = []

    print(f"Processing {len(test_df)} questions from {testset_csv_path}...")
    for index, row in tqdm(test_df.iterrows(), total=test_df.shape[0], desc=f"Evaluating {base_name}"):
        question = row["user_input"]
        ground_truth = str(row["reference"])
        # Pass the session to the API call function
        tool_response = await get_internal_docs_tool_response(question, session)
        questions.append(question)
        ground_truths.append(ground_truth)
        answers.append(tool_response["answer"])
        retrieved_contexts_list.append(tool_response["contexts"])

    ragas_data = {
        "question": questions,
        "answer": answers,
        "contexts": retrieved_contexts_list,
        "ground_truth": ground_truths
    }
    ragas_dataset = Dataset.from_dict(ragas_data)

    print(f"Running RAGAS metrics for {base_name}...")
    metrics_to_evaluate = [
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
        answer_correctness # Added answer_correctness
    ]
    
    try:
        result = evaluate(ragas_dataset, metrics=metrics_to_evaluate, raise_exceptions=False)
        print(f"RAGAS Evaluation complete for {base_name}.")
        
        average_scores = {}
        per_item_scores_df = pd.DataFrame() # Initialize an empty DataFrame

        if hasattr(result, 'to_pandas'):
            try:
                per_item_scores_df = result.to_pandas()
            except Exception as e_to_pandas:
                print(f"Warning: result.to_pandas() failed: {e_to_pandas}. Will attempt to build averages from result directly.")
                # Fallback if to_pandas fails, try to use the result object if it's dict-like
                if isinstance(result, (dict, UserDict, Mapping)):
                    # If result contains lists of scores per metric
                    for metric_name, scores_list in result.items():
                        if isinstance(scores_list, list) and scores_list:
                            try:
                                numeric_scores = pd.to_numeric(scores_list, errors='coerce')
                                mean_val = pd.Series(numeric_scores).dropna().mean()
                                average_scores[metric_name] = float(mean_val) if pd.notna(mean_val) else None
                            except Exception as e_avg_fallback:
                                print(f"Warning: Could not calculate average for metric '{metric_name}' from fallback: {e_avg_fallback}")
                                average_scores[metric_name] = None
                        elif isinstance(scores_list, (float, int)): # if result was already averaged by chance
                             average_scores[metric_name] = float(scores_list)
                # per_item_scores_df would remain empty or contain partial data from dataset if we reconstruct

        if not per_item_scores_df.empty:
            print(f"Calculating average scores from per-item DataFrame for {base_name}...")
            for metric_col_name in per_item_scores_df.columns:
                # Check if this column name is one of the metrics we are evaluating
                is_metric_column = any(m.name == metric_col_name for m in metrics_to_evaluate)
                if is_metric_column:
                    try:
                        numeric_scores = pd.to_numeric(per_item_scores_df[metric_col_name], errors='coerce')
                        mean_val = numeric_scores.dropna().mean()
                        average_scores[metric_col_name] = float(mean_val) if pd.notna(mean_val) else None
                    except Exception as e_avg:
                        print(f"Warning: Could not calculate average for metric '{metric_col_name}': {e_avg}")
                        average_scores[metric_col_name] = None
        elif not average_scores: # If to_pandas failed AND fallback didn't populate averages
            print(f"Warning: Could not obtain per-item scores DataFrame via to_pandas() nor calculate averages from result object for {base_name}. Original Ragas result: {result}")

        # Ensure all average scores are JSON-friendly (Python floats)
        final_average_scores = {k: float(v) if isinstance(v, (int, float)) and pd.notna(v) else None for k, v in average_scores.items()}
        final_average_scores = {k: v for k, v in final_average_scores.items() if v is not None} # Remove None entries for cleaner JSON

        print(f"Average scores for {base_name}: {final_average_scores}")
        
        # Save the detailed per-item scores to CSV if available, otherwise save averages or empty.
        if not per_item_scores_df.empty:
            print(f"Saving detailed RAGAS evaluation CSV to {output_csv_file}")
            per_item_scores_df.to_csv(output_csv_file, index=False)
        elif final_average_scores: # If we only have averages, save those
            print(f"Saving average RAGAS evaluation scores to CSV: {output_csv_file}")
            pd.DataFrame([final_average_scores]).to_csv(output_csv_file, index=False)
        else:
            print(f"No scores to save to CSV for {base_name}. Creating empty CSV.")
            pd.DataFrame().to_csv(output_csv_file, index=False)
            
        # Save the average scores to JSON
        print(f"Summary RAGAS (average) scores saved to {output_json_file}")
        with open(output_json_file, 'w') as f:
            json.dump(final_average_scores, f, indent=4)

    except Exception as e:
        print(f"Error during RAGAS evaluation for {base_name}: {e}")
        if 'ragas_dataset' in locals(): # Print data if available
             print(f"Data prepared for {base_name}:")
             print(ragas_dataset.to_pandas().head())
        # Also print any problematic result if available
        if 'result' in locals() and result:
            print(f"Problematic Ragas result object: {result}")
             
    print(f"--- Finished evaluation for testset: {testset_csv_path} ---")


async def main():
    # await initialize_retriever() # REMOVED
    
    testset_input_dir = "generated_testsets"
    results_output_dir = "ragas_evaluation_results"

    if not os.path.exists(results_output_dir):
        os.makedirs(results_output_dir)

    testset_files = glob.glob(os.path.join(testset_input_dir, "testset_*.csv"))

    if not testset_files:
        print(f"No testset CSV files found in {testset_input_dir}. Exiting.")
        return

    print(f"Found {len(testset_files)} testsets to evaluate: {testset_files}")

    # Create a single aiohttp session to be reused for all API calls
    async with aiohttp.ClientSession() as session:
        for testset_file_path in testset_files:
            await run_evaluation_for_testset(testset_file_path, results_output_dir, session)


# REMOVED initialize_retriever_sync_fallback function

if __name__ == "__main__":
    asyncio.run(main()) 