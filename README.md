# AI COO Shopify Agent PoC

A Proof of Concept (PoC) agentic AI chatbot with a React/Next.js frontend and FastAPI backend. The agent simulates answering operational questions for a $1M-$20M Shopify merchant using synthetic data.

## Project Overview

This PoC demonstrates an AI assistant that can help Shopify merchants analyze their sales velocity and inventory levels. The assistant uses synthetic data to simulate integration with Shopify's API.

### Core Focus

The agent focuses on answering questions related to:
- Sales velocity for specific products
- Inventory levels and projections
- Product performance metrics

## Technology Stack

- **Frontend**: Next.js with TypeScript and Tailwind CSS
- **Backend**: FastAPI (Python)
- **Package Management**: uv (Python) & npm (JavaScript)
- **Agent Framework**: LangGraph (based on LangChain)
- **AI Integration**: OpenAI GPT-4o / Claude 3.5 Sonnet
- **Synthetic Data**: Generated with Faker and Pandas
- **Evaluation**: Ragas for agent performance assessment

## Project Structure

```
/
├── backend/               # FastAPI backend
│   ├── app/               # Application code
│   │   ├── tools.py       # Agent tools for querying data
│   │   ├── agent.py       # LangGraph agent implementation
│   │   └── __init__.py    
│   ├── data/              # Synthetic data (generated)
│   ├── data_generator.py  # Script to generate synthetic data
│   ├── evaluation.py      # Evaluation utilities with Ragas
│   ├── main.py            # FastAPI application entry point
│   ├── pyproject.toml     # Project dependencies and metadata
│   └── Dockerfile         # Backend container definition
│
├── frontend/              # Next.js frontend
│   ├── app/               # Next.js 13+ app directory
│   ├── components/        # React components
│   │   ├── ChatInput.tsx  # User input component
│   │   ├── ChatMessage.tsx # Message display component
│   │   └── ChatWindow.tsx # Main chat interface
│   ├── Dockerfile         # Frontend container definition
│   └── ... other Next.js files
│
├── docker-compose.yml     # Docker Compose configuration
└── README.md              # Project documentation
```

## Agent Graph Visualization

The following Mermaid diagram illustrates the core operational flow of the LangGraph agent:

```mermaid
graph TD
    %% Nodes
    A["__start__"]:::startNode
    B["chatbot"]:::llmNode
    C_PRODUCT_INFO["get_product_info"]:::toolNode
    C_LIST_PRODUCTS["list_products"]:::toolNode
    C_INVENTORY["get_inventory_level"]:::toolNode
    C_LOW_STOCK["list_low_stock_products"]:::toolNode
    C_SALES_DATA["get_sales_data_for_product"]:::toolNode
    C_STOCK_REMAINING["estimate_days_of_stock_remaining"]:::toolNode
    C_TOP_SELLING["get_top_selling_products"]:::toolNode
    C_INTERNAL_DOCS["query_internal_documents"]:::toolNode
    D["__end__"]:::endNode

    %% Edges
    A --> B; %% Start to chatbot

    B -- "LLM decides to use get_product_info" --> C_PRODUCT_INFO;
    C_PRODUCT_INFO -- "Tool output returned" --> B;

    B -- "LLM decides to use list_products" --> C_LIST_PRODUCTS;
    C_LIST_PRODUCTS -- "Tool output returned" --> B;

    B -- "LLM decides to use get_inventory_level" --> C_INVENTORY;
    C_INVENTORY -- "Tool output returned" --> B;

    B -- "LLM decides to use list_low_stock_products" --> C_LOW_STOCK;
    C_LOW_STOCK -- "Tool output returned" --> B;

    B -- "LLM decides to use get_sales_data_for_product" --> C_SALES_DATA;
    C_SALES_DATA -- "Tool output returned" --> B;

    B -- "LLM decides to use estimate_days_of_stock_remaining" --> C_STOCK_REMAINING;
    C_STOCK_REMAINING -- "Tool output returned" --> B;

    B -- "LLM decides to use get_top_selling_products" --> C_TOP_SELLING;
    C_TOP_SELLING -- "Tool output returned" --> B;

    B -- "LLM decides to use query_internal_documents" --> C_INTERNAL_DOCS;
    C_INTERNAL_DOCS -- "Tool output returned" --> B;

    B -- "LLM generates final answer" --> D; %% Chatbot to End

    %% Styling (optional)
    classDef startNode fill:#D5E8D4,stroke:#82B366,stroke-width:2px;
    classDef llmNode fill:#DAE8FC,stroke:#6C8EBF,stroke-width:2px;
    classDef toolNode fill:#FFE6CC,stroke:#D79B00,stroke-width:2px;
    classDef endNode fill:#F8CECC,stroke:#B85450,stroke-width:2px;
```

**Explanation of the Flow:**
1.  The process begins at `__start__` and enters the `chatbot` node.
2.  The `chatbot` node, powered by an LLM, analyzes the user's query.
3.  If the LLM determines that a tool is necessary to gather information or perform an action, it transitions to the `tools` node.
4.  The `tools` node (which is a custom dispatcher) executes the specific tool required (e.g., `get_product_info`, `query_internal_documents`).
5.  The output from the executed tool is then sent back to the `chatbot` node.
6.  The `chatbot` node re-evaluates the situation with the new information. It may generate a final answer, or it might decide to call another tool (repeating steps 3-5).
7.  Once the `chatbot` can provide a final answer without needing more tool interventions, it transitions to `__end__`.

This cyclic interaction between the `chatbot` and `tools` nodes allows the agent to iteratively gather information and build towards a comprehensive answer.

## RAG Pipeline Evaluation (Retriever Focus)

An evaluation of the RAG pipeline's retrieval component was performed using RAGAS. The test used concatenated retrieved contexts as the "answer" to specifically assess the retriever's performance.

**Testset:** `generated_testsets/testset_kg_knowledge_base.csv` (81 questions)

**Average Scores:**
- **Faithfulness:** 0.9979
- **Answer Relevancy (of contexts):** 0.8410
- **Context Precision:** 0.8711
- **Context Recall:** 0.7967
- **Answer Correctness (contexts vs. ground truth answer):** 0.4122

**Analysis:**

The retrieval component of the RAG pipeline demonstrates strong performance in finding relevant and factually consistent information:

- **Strengths:**
    - **High Faithfulness (0.9979):** The retrieved contexts are internally consistent and factually grounded.
    - **Good Context Precision (0.8711):** The retriever is effective at fetching relevant documents with a good signal-to-noise ratio.
    - **Good Answer Relevancy (0.8410):** The content of the retrieved documents is generally relevant to the questions posed.

- **Areas for Improvement & Key Observations:**
    - **Context Recall (0.7967):** While fair, this indicates that about 80% of the necessary information from the ground truth is captured within the retrieved contexts. There's room to improve this, potentially by optimizing chunking, embedding models, or retrieval top-k settings.
    - **Low Answer Correctness (0.4122):** This is a critical finding. This metric compares the concatenated retrieved contexts against the ideal ground truth answer. The low score clearly highlights that raw retrieved documents, even if relevant, are not a substitute for a synthesized, well-formed answer. This strongly indicates the need for a **generator model (LLM)** to process these contexts.

**Conclusions & Recommendations:**

1.  **Solid Retriever Foundation:** The current retrieval mechanism (vector store, embeddings) is performing well in identifying and fetching relevant information.
2.  **Essential Generator Step:** The low `answer_correctness` underscores the necessity of an LLM-based generator. This component would take the retrieved contexts and the original query to synthesize a coherent and accurate final answer.
3.  **Path Forward:**
    *   **Implement a Generator:** Integrate an LLM to generate answers based on the retrieved contexts. The RAGAS evaluation should then use this LLM-generated answer, which is expected to significantly improve `answer_correctness`.
    *   **Iterate on Retrieval (If Needed):** After implementing a generator, if `context_recall` or other retrieval metrics remain a concern, further fine-tuning of the retrieval process can be explored.

This evaluation confirms that the retrieval stage is a robust starting point. The next crucial step is the addition of a generation layer to transform retrieved data into high-quality answers.

## RAG Pipeline Evaluation (Retriever Focus - With Finetuned Embedding Model)

Following an attempt to integrate a finetuned embedding model, a subsequent evaluation was performed on the retrieval component using the same methodology (concatenated contexts as the "answer").

**Testset:** `generated_testsets/testset_kg_knowledge_base.csv` (81 questions)

**Average Scores (with Finetuned Model):**
- **Faithfulness:** 0.9813
- **Answer Relevancy (of contexts):** 0.8490
- **Context Precision:** 0.8398
- **Context Recall:** 0.7687
- **Answer Correctness (contexts vs. ground truth answer):** 0.3698

**(For reference, Baseline Scores were: Faithfulness: 0.9979, Answer Relevancy: 0.8410, Context Precision: 0.8711, Context Recall: 0.7967, Answer Correctness: 0.4122)**

**Analysis of "Finetuned" Model Results:**

The introduction of this particular finetuned embedding model showed mixed results, with some key retrieval metrics performing slightly below the baseline:

- **Observed Changes:**
    - **Faithfulness (0.9813):** Remained very high, with a negligible decrease from the baseline (0.9979).
    - **Answer Relevancy (0.8490):** Showed a slight improvement over the baseline (0.8410).
    - **Context Precision (0.8398):** Decreased compared to the baseline (0.8711), suggesting the retrieved contexts might have a slightly lower signal-to-noise ratio.
    - **Context Recall (0.7687):** Decreased from the baseline (0.7967), indicating that this version of the retriever captured less of the necessary information.
    - **Answer Correctness (0.3698):** Decreased from the baseline (0.4122), reflecting the changes in context quality.

- **Interpretation & Concerns:**
    - The dip in `context_precision` and `context_recall` suggests that this specific finetuning iteration might not have been optimal for improving these general retrieval qualities or could have inadvertently affected them while optimizing for other aspects.
    - It highlights the importance of rigorous A/B testing against a baseline when introducing changes like model finetuning.

**Conclusions & Recommendations (Post-"Finetuning" Attempt):**

1.  **Re-evaluate Finetuning Strategy:** The results indicate a need to review the finetuning process for the embedding model (dataset, methodology, objectives) to ensure it leads to clear improvements over the baseline retriever across desired metrics.
2.  **Generator Remains Critical:** The `answer_correctness` score, even with different retriever configurations, consistently underscores the necessity of an LLM-based generator to synthesize final answers from retrieved contexts.
3.  **Prioritize Generator Implementation:** Regardless of ongoing retriever optimization, implementing and evaluating a generator component should be a primary focus. The generator can be tested with both the baseline and any improved retriever versions.

This round of evaluation emphasizes that enhancing one component (like the embedding model through finetuning) requires careful validation to ensure overall pipeline improvement. The fundamental need for a strong generation stage remains evident.

## Getting Started

### Prerequisites

- Docker and Docker Compose (recommended)
- Node.js 20+ and npm (for frontend development)
- Python 3.9+ (for backend development)
- uv package manager (recommended over pip)
- OpenAI API key or Anthropic API key

### Important: Data Generation

The application requires synthetic Shopify data to function. There are two ways to generate this data:

1. **Automatically with Docker**: When using docker-compose, the backend container will automatically generate the data on startup.

2. **Manually for development**:
   ```bash
   cd backend
   # With uv (recommended)
   uv run python data_generator.py
   
   # Or with standard Python
   python data_generator.py
   ```

This will create the following dataset files in the `backend/data/` directory:
- `products.csv`: Product catalog with IDs, names, prices, etc.
- `inventory.csv`: Current inventory levels for each product
- `orders.csv`: Order history for the past 90 days
- `order_items.csv`: Line items for each order

**You must generate this data before starting the backend in development mode.**

### Running with Docker Compose

1. Create a `.env` file in the project root with:
   ```
   OPENAI_API_KEY=your_openai_api_key
   # OR
   ANTHROPIC_API_KEY=your_anthropic_api_key
   ```

2. Start the application (data will be generated automatically):
   ```bash
   docker-compose up
   ```

3. Open your browser to http://localhost:3000

### Development Setup

#### Using uv (recommended)

[uv](https://github.com/astral-sh/uv) is a fast, reliable Python package installer and resolver. To get started:

1. Install uv:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Navigate to the backend directory and install dependencies:
   ```bash
   cd backend
   uv sync
   ```

3. Run the data generator:
   ```bash
   uv run python data_generator.py
   ```

4. Start the FastAPI server:
   ```bash
   uv run uvicorn main:app --reload
   ```

#### Traditional Python Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt  # or: uv pip install -r requirements.txt
   ```

3. **Generate synthetic data** (must be done before starting the server):
   ```bash
   python data_generator.py
   ```
   This will create all necessary CSV files in the `backend/data/` directory.

4. Start the FastAPI server:
   ```bash
   uvicorn main:app --reload
   ```

#### Frontend

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Create a `.env.local` file with:
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

4. Start the development server:
   ```bash
   npm run dev
   ```

### Evaluation

To evaluate the agent's performance (make sure data is generated first):

```bash
cd backend
# Using uv
uv run python evaluation.py

# Or traditional Python
python evaluation.py
```

## Sample Questions

- "What were the total sales for Product ID 'P123' in the last 30 days?"
- "How many units of Product ID 'P456' are currently in stock?"
- "What is the average daily sales quantity for 'P123' over the past month?"
- "Estimate the days of stock remaining for 'P456' based on the last 30 days of sales."
- "List products with less than 10 units in stock."
- "What products should we reorder immediately based on stock status?"

## Deployment

The application is containerized and can be deployed to any Docker-compatible hosting platform such as:

- Railway
- Fly.io
- Google Cloud Run
- AWS ECS
- Azure Container Apps

## Troubleshooting

### Common Issues

1. **"No data found" errors**: Ensure you've generated the data by running `python data_generator.py` in the backend directory or by using Docker Compose which does this automatically.

2. **API Connection Issues**: Make sure the backend is running and the `NEXT_PUBLIC_API_URL` in the frontend's `.env.local` file is correctly pointing to your backend server.

3. **LLM API Errors**: Verify that you've set either the `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` environment variable.

4. **uv Installation Issues**: If you have trouble with uv, check the [official documentation](https://github.com/astral-sh/uv) for platform-specific installation instructions.

## Future Improvements

- Integration with real Shopify API
- Addition of marketing analysis capabilities  
- Enhanced data visualization
- User authentication
- Persistent conversation history
