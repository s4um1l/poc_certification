import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from app.agent import get_agent_response

# Create FastAPI app
app = FastAPI(
    title="AI COO Shopify Agent",
    description="An AI agent that provides insights about sales velocity and inventory levels.",
    version="0.1.0"
)

# Configure CORS
origins = [
    "http://localhost:3000",  # Next.js default port
    "http://localhost:5173",  # Vite default port
    # Add your deployed frontend URL when available
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define request and response models
class QueryRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    response: str

# Health check endpoint
@app.get("/")
async def read_root():
    return {
        "status": "ok",
        "message": "AI COO Agent Backend is running"
    }

# Chat endpoint
@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_agent(request: QueryRequest):
    try:
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        response = get_agent_response(request.query)
        return ChatResponse(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Create a .env file if it doesn't exist
if not os.path.exists(".env"):
    with open(".env", "w") as f:
        f.write("# Add your API keys here\n")
        f.write("# OPENAI_API_KEY=your-key-here\n")
        f.write("# ANTHROPIC_API_KEY=your-key-here\n")

# Run the app with uvicorn when executed directly
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 