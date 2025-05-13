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
