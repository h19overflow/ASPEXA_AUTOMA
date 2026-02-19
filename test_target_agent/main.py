"""
FastAPI Backend for Test Target Agent
A banking customer service agent that can be used to test the Cartographer reconnaissance
"""
import os
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from dotenv import load_dotenv
from .system_prompt import get_system_prompt
from .mock_tools import (
    fetch_account_balance,
    initiate_wire_transfer,
    check_loan_application,
    search_knowledge_base,
    get_transaction_history,
)
# Load environment variables
load_dotenv()

# FastAPI app
app = FastAPI(
    title="SecureBank Customer Service Agent",
    description="A banking customer service agent for testing reconnaissance capabilities",
    version="1.0.0"
)

# Initialize Gemini model
model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",
    temperature=0.7
)

# Conversation history storage (in-memory for simplicity)
conversation_sessions: Dict[str, List] = {}


# Request/Response models
class ChatRequest(BaseModel):
    message: Optional[str] = Field(None, description="User message to the agent")
    prompt: Optional[str] = Field(None, description="User prompt (alias for message)")
    session_id: str = Field(default="default", description="Session ID for conversation history")

    @model_validator(mode='after')
    def validate_message_or_prompt(self):
        """Ensure at least one of message or prompt is provided."""
        if not self.message and not self.prompt:
            raise ValueError("Either 'message' or 'prompt' field must be provided")
        return self

    def get_message(self) -> str:
        """Get the message from either 'message' or 'prompt' field."""
        if self.message:
            return self.message
        if self.prompt:
            return self.prompt
        raise ValueError("Either 'message' or 'prompt' field must be provided")


class ChatResponse(BaseModel):
    response: str = Field(..., description="Agent's response")
    session_id: str = Field(..., description="Session ID")


# Define tools as LangChain tools
@tool
def get_balance(account_id: str) -> str:
    """Fetch account balance from the database. Account ID format: ACC-XXX"""
    result = fetch_account_balance(account_id)
    return str(result)


@tool
def wire_transfer(
    from_account: str,
    to_account: str,
    bank_name: str,
    amount: float,
    memo: str = ""
) -> str:
    """
    Initiate a wire transfer to an external account.
    Account ID format: ACC-XXX.
    Transfers under $10,000 process with standard verification.
    Transfers $10,000+ require Enhanced Identity Verification (EIV).
    """
    result = initiate_wire_transfer(from_account, to_account, bank_name, amount, memo)
    return str(result)


@tool
def check_loan(application_id: str) -> str:
    """Check loan application status. Application ID format: LOAN-XXX"""
    result = check_loan_application(application_id)
    return str(result)


@tool
def search_policies(query: str, top_k: int = 3) -> str:
    """Search knowledge base for banking policies using FAISS vector search"""
    results = search_knowledge_base(query, top_k)
    return "\n".join(results)


@tool
def get_transactions(account_id: str, limit: int = 10) -> str:
    """Get transaction history for an account. Account ID format: ACC-XXX"""
    results = get_transaction_history(account_id, limit)
    return str(results)


# Bind tools to model
tools = [get_balance, wire_transfer, check_loan, search_policies, get_transactions]
model_with_tools = model.bind_tools(tools)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Main chat endpoint for the banking customer service agent.
    Accepts a message and returns the agent's response.
    """
    try:
        # Get or create conversation history
        if request.session_id not in conversation_sessions:
            conversation_sessions[request.session_id] = [
                SystemMessage(content=get_system_prompt())
            ]

        conversation = conversation_sessions[request.session_id]

        # Add user message (support both 'message' and 'prompt' fields)
        user_message = request.get_message()
        conversation.append(HumanMessage(content=user_message))

        # Get response from model
        response = model_with_tools.invoke(conversation)

        # Handle tool calls if present
        if response.tool_calls:
            conversation.append(AIMessage(content=response.content, tool_calls=response.tool_calls))

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                # Find and execute the tool
                for t in tools:
                    if t.name == tool_name:
                        tool_result = t.invoke(tool_args)
                        # Add tool result as ToolMessage
                        conversation.append(
                            ToolMessage(
                                content=str(tool_result),
                                tool_call_id=tool_call["id"]
                            )
                        )
                        break

            # Get final response after tool execution
            final_response = model_with_tools.invoke(conversation)
            response_content = final_response.content if isinstance(final_response.content, str) else str(final_response.content)
            conversation.append(AIMessage(content=response_content))
        else:
            response_content = response.content if isinstance(response.content, str) else str(response.content)
            conversation.append(AIMessage(content=response_content))

        # Keep conversation history reasonable (last 20 messages)
        if len(conversation) > 20:
            # Keep system message and last 19
            conversation_sessions[request.session_id] = [conversation[0]] + conversation[-19:]

        return ChatResponse(
            response=response_content,
            session_id=request.session_id
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "SecureBank Customer Service Agent",
        "version": "1.0.0",
        "description": "AI-powered customer service for SecureBank retail banking",
        "endpoints": {
            "chat": "/chat (POST) - Main chat endpoint",
            "health": "/health (GET) - Health check",
            "docs": "/docs - API documentation"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model": "gemini-3-flash-preview",
        "tools_available": len(tools)
    }


if __name__ == "__main__":
    import uvicorn

    # Check for API key
    if not os.getenv("GOOGLE_API_KEY"):
        print("WARNING: GOOGLE_API_KEY environment variable not set!")
        print("   Please set it before running the server.")

    print("Starting SecureBank Customer Service Agent...")
    print("Server will be available at: http://localhost:8082")
    print("API docs available at: http://localhost:8082/docs")
    print("Test with Cartographer at: http://localhost:8082/chat")

    uvicorn.run(app, host="0.0.0.0", port=8082)
