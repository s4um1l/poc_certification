import asyncio
import glob
import os
from pathlib import Path
import logging

import pandas as pd
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document as LangchainDocument
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import DirectoryLoader

# Ragas specific imports for the unrolled approach
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.testset.graph import KnowledgeGraph, Node, NodeType
from ragas.testset.transforms import apply_transforms, default_transforms

# Explicitly import transforms we will use
# from ragas.testset.transforms import (
#     SummaryExtractor, 
#     EmbeddingExtractor, 
#     TitleExtractor, # Changed from ThemesExtractor
#     KeyphrasesExtractor, # Changed from NERExtractor
#     CosineSimilarityBuilder,
#     # OverlapScoreBuilder # Still disabled
# )
# We will not use default_transforms for now to have more control
# try:
#     from ragas.testset.transforms import default_transforms
# except ImportError:
#     default_transforms = None 

from ragas.testset import TestsetGenerator
from ragas.testset.synthesizers import (
    SingleHopSpecificQuerySynthesizer,
    MultiHopAbstractQuerySynthesizer,
    MultiHopSpecificQuerySynthesizer
)


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
# Directories
SOURCE_DIR = Path(__file__).parent / "knowledge_base"
OUTPUT_DIR = Path(__file__).parent / "generated_testsets"
OUTPUT_DIR.mkdir(exist_ok=True)

# Ragas Testset Generation Parameters
N_QUESTIONS_PER_DOC = int(os.environ.get("N_QUESTIONS_PER_DOC", 100)) # Reduced for testing, notebook uses 10 for 2 docs
# MAX_DOC_LENGTH_CHARS = 30000 # Less relevant if pre-chunking

# Chunking parameters for initial KG node creation
# INITIAL_CHUNK_SIZE = int(os.environ.get("INITIAL_CHUNK_SIZE", 350)) # Smaller initial chunks
# INITIAL_CHUNK_OVERLAP = int(os.environ.get("INITIAL_CHUNK_OVERLAP", 30))


def generate_testset_for_document(source_file_path: Path, output_dir: Path, generator_llm_wrapper: LangchainLLMWrapper, embedding_model_wrapper: LangchainEmbeddingsWrapper):
    """
    Generates a testset for a single document using Ragas (Unrolled SDG with Knowledge Graph, using default_transforms).
    """
    logger.info(f"--- Starting processing for: {source_file_path.name} ---")
    print(f"Processing document: {source_file_path}")
    

    path = source_file_path
    loader = DirectoryLoader(path, glob="*.txt")
    docs = loader.load()

    # Document content and metadata are primarily for the default_transforms context if needed,
    # and for direct addition to KG as DOCUMENT nodes.
    # doc_content = raw_langchain_docs[0].page_content 
    # doc_metadata = raw_langchain_docs[0].metadata.copy()

    # 1. Initialize an empty KnowledgeGraph
    kg = KnowledgeGraph()
    logger.info(f"Initialized empty KnowledgeGraph for {source_file_path.name}")

    # 2. Add raw Langchain documents as NodeType.DOCUMENT to the KG
    # default_transforms will then operate on these DOCUMENT nodes.
    for doc in docs:
        kg.nodes.append(
            Node(
                type=NodeType.DOCUMENT,
                properties={"page_content": doc.page_content, "document_metadata": doc.metadata}
            )
        )
    logger.info(f"Added {len(docs)} DOCUMENT nodes to KG for {source_file_path}.")
    print(f"Initial KG for {source_file_path} (from raw docs): {kg}")


    # 3. Get default transformations from Ragas
    # These transforms will process the DOCUMENT nodes and enrich the KG (chunking, summaries, entities, etc.)
    logger.info(f"Getting default_transforms for {source_file_path}...")
    try:
        # Pass the raw Langchain documents to default_transforms
        transforms_to_apply = default_transforms(
            documents=docs, 
            llm=generator_llm_wrapper, 
            embedding_model=embedding_model_wrapper
        )
        logger.info(f"Obtained {len(transforms_to_apply)} default_transforms for {source_file_path.name}.")
        print(f"DEBUG: Default transforms for {source_file_path.name}: {transforms_to_apply}")
    except Exception as e:
        logger.error(f"Error obtaining default_transforms for {source_file_path.name}: {e}", exc_info=True)
        print(f"Error obtaining default_transforms for {source_file_path.name}: {e}")
        return

    logger.info(f"Applying {len(transforms_to_apply)} default transformations to KG for {source_file_path.name}")
    print(f"Applying default transformations to KG for {source_file_path.name}...")
    try:
        apply_transforms(kg, transforms_to_apply) 
        logger.info(f"Finished applying default transforms. KG for {source_file_path.name}: {kg}")
        print(f"Finished default transformations. KG for {source_file_path.name}: {kg}")
        
        # Detailed KG logging
        logger.info(f"--- KG Details for {source_file_path.name} POST-TRANSFORM ---")
        for i, node in enumerate(kg.nodes):
            logger.info(f"Node {i}: id={node.id}, type={node.type}, properties={node.properties}")
        for i, rel in enumerate(kg.relationships):
            logger.info(f"Relationship {i}: source_id={rel.source.id if rel.source else None}, target_id={rel.target.id if rel.target else None}, type={rel.type}, properties={rel.properties}")
        logger.info(f"--- End KG Details for {source_file_path.name} ---")

    except Exception as e:
        logger.error(f"Error applying default transforms for {source_file_path.name}: {e}", exc_info=True)
        print(f"Error applying default transforms for {source_file_path.name}: {e}")
        return

    try:
        generator = TestsetGenerator(
            llm=generator_llm_wrapper,
            embedding_model=embedding_model_wrapper,
            knowledge_graph=kg
        )
        logger.info(f"Initialized TestsetGenerator with KG for {source_file_path.name}")
    except Exception as e:
        logger.error(f"Error initializing TestsetGenerator for {source_file_path.name}: {e}", exc_info=True)
        print(f"Error initializing TestsetGenerator for {source_file_path.name}: {e}")
        return

    kg_nodes_count = len(kg.nodes)
    kg_relationships_count = len(kg.relationships)
    logger.info(f"KG for {source_file_path.name} has {kg_nodes_count} nodes and {kg_relationships_count} relationships.")

    # Temporarily force SingleHopSpecificQuerySynthesizer to isolate clustering issue
    logger.warning(f"FORCED: Using SingleHopSpecificQuerySynthesizer only for {source_file_path.name} to debug clustering.")
    print(f"DEBUG: FORCING SingleHopSpecificQuerySynthesizer for {source_file_path.name}.")
    query_distribution_config = [
        (SingleHopSpecificQuerySynthesizer(llm=generator_llm_wrapper), 1.0)
    ]
    if kg_nodes_count < 3 or kg_relationships_count < 2: 
        logger.warning(f"KG for {source_file_path.name} is sparse ({kg_nodes_count} nodes, {kg_relationships_count} rels). Using SingleHopSpecificQuerySynthesizer only.")
        print(f"WARNING: KG for {source_file_path.name} is sparse. Using SingleHopSpecificQuerySynthesizer only.")
        query_distribution_config = [
            (SingleHopSpecificQuerySynthesizer(llm=generator_llm_wrapper), 1.0)
        ]
    else:
        logger.info(f"KG for {source_file_path.name} is sufficiently dense ({kg_nodes_count} nodes, {kg_relationships_count} rels). Using mixed query distribution.")
        query_distribution_config = [
            (SingleHopSpecificQuerySynthesizer(llm=generator_llm_wrapper), 0.4),
            (MultiHopAbstractQuerySynthesizer(llm=generator_llm_wrapper), 0.3),
            (MultiHopSpecificQuerySynthesizer(llm=generator_llm_wrapper), 0.3),
        ]
    
    logger.info(f"Defined query distribution for {source_file_path.name}: {[(s.__class__.__name__, w) for s, w in query_distribution_config]}")
    
    actual_test_size = N_QUESTIONS_PER_DOC
    logger.info(f"Generating {actual_test_size} test samples for {source_file_path.name} using KG...")
    print(f"Generating {actual_test_size} test samples for {source_file_path.name} using KG...")
    
    try:
        test_samples_dataset = generator.generate(
            testset_size=actual_test_size,
            query_distribution=query_distribution_config
        )
        test_samples_df = test_samples_dataset.to_pandas()
    except Exception as e:
        logger.error(f"Error during testset generation for {source_file_path.name}: {e}", exc_info=True)
        print(f"Error during testset generation for {source_file_path.name}: {e}")
        # If no samples generated, df might be None or raise error on .to_pandas()
        # Catch this and return to avoid further errors on empty df
        if "No test data generated" in str(e) or "No questions generated" in str(e) or "No nodes that satisfied" in str(e):
             logger.warning(f"Testset generation yielded no samples for {source_file_path.name} due to: {e}")
             print(f"WARNING: Testset generation yielded no samples for {source_file_path.name} due to: {e}")
             return
        raise # Re-raise if it's a different error

    if test_samples_df is None or test_samples_df.empty:
        logger.warning(f"No test samples were generated (DataFrame is empty/None) for {source_file_path.name}. Skipping file save.")
        print(f"WARNING: No test samples were generated (DataFrame is empty/None) for {source_file_path.name}. Skipping file save.")
        return

    print(f"Generated {len(test_samples_df)} samples for {source_file_path.name}.")
    logger.info(f"Generated {len(test_samples_df)} samples for {source_file_path.name}.")

    column_mapping = {
        "question": "user_input",
        "ground_truth": "reference",
        "contexts": "reference_contexts",
        "evolution_type": "evolution_type" 
    }
    
    actual_columns = test_samples_df.columns
    renamed_columns = {}
    for ragas_col, desired_col in column_mapping.items():
        if ragas_col in actual_columns:
            renamed_columns[ragas_col] = desired_col
    
    if renamed_columns:
        test_samples_df = test_samples_df.rename(columns=renamed_columns)
        logger.info(f"Renamed columns for {source_file_path.name}.") 

    expected_final_columns = ["user_input", "reference", "reference_contexts", "evolution_type"]
    for col in expected_final_columns:
        if col not in test_samples_df.columns:
            test_samples_df[col] = None 
            logger.warning(f"Column '{col}' was missing. Added it with None values for {source_file_path.name}.")

    output_file_path = output_dir / f"testset_kg_{source_file_path.stem}.csv"
    test_samples_df_to_save = test_samples_df[[col for col in expected_final_columns if col in test_samples_df.columns]]
    
    test_samples_df_to_save.to_csv(output_file_path, index=False)
    logger.info(f"Successfully saved KG-based testset to {output_file_path}")
    print(f"Testset saved to {output_file_path}")
    logger.info(f"--- Finished processing for: {source_file_path} ---\n")


def main():
    """
    Main function to generate testsets for all .txt files in the source directory.
    Synchronous version based on notebook's unrolled SDG.
    """
    load_dotenv() 

    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY not found. Please set it up in .env file.")
        print("OPENAI_API_KEY not found. Please set it in your .env file.")
        return

    # Initialize LLM and Embeddings Wrappers once
    generator_llm_model = os.environ.get("RAGAS_GENERATOR_LLM", "gpt-4.1-nano")

    logger.info(f"Using generator LLM: {generator_llm_model}")

    generator_llm_wrapper = LangchainLLMWrapper(ChatOpenAI(model=generator_llm_model))
    embedding_model_wrapper = LangchainEmbeddingsWrapper(OpenAIEmbeddings())
    
    # Check Ragas version for compatibility if needed
    try:
        import ragas
        logger.info(f"Using Ragas version: {ragas.__version__}")
        # Removed version check for 0.2.10, as 0.2.15 is what's installed.
        # We are adapting to the installed version based on documentation and trial.
    except ImportError:
        logger.error("Ragas not installed.")
        return


    source_files = list(SOURCE_DIR.glob("*.txt"))
    if not source_files:
        logger.warning(f"No .txt files found in {SOURCE_DIR}. Exiting.")
        print(f"No .txt files found in {SOURCE_DIR}. Exiting.")
        return

    logger.info(f"Found {len(source_files)} documents to process in {SOURCE_DIR}.")
    print(f"Found {len(source_files)} documents to process.")

    try:
        # Pass all files at once to generate_testset_for_document
        generate_testset_for_document(SOURCE_DIR, OUTPUT_DIR, generator_llm_wrapper, embedding_model_wrapper)
    except Exception as e:
        logger.error(f"Unhandled exception while processing documents: {e}", exc_info=True)
        print(f"Failed to process documents due to an unhandled error: {e}")
    logger.info("All documents processed.")
    print("All documents processed.")

if __name__ == "__main__":
    # Previous version was async, notebook version is sync.
    # asyncio.run(main_async())
    main() 