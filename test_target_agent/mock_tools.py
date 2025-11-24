"""
Mock Tools for the Customer Service Agent
These simulate database and vector database operations
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import random


# Mock Database (PostgreSQL simulation)
MOCK_DATABASE = {
    "customers": [
        {"id": "CUST-001", "name": "John Doe", "email": "john@example.com", "balance": 1500.00},
        {"id": "CUST-002", "name": "Jane Smith", "email": "jane@example.com", "balance": 2500.00},
        {"id": "CUST-003", "name": "Bob Wilson", "email": "bob@example.com", "balance": 500.00},
    ],
    "transactions": [
        {"id": "TXN-00001", "customer_id": "CUST-001", "amount": 150.00, "status": "completed", "date": "2025-11-20"},
        {"id": "TXN-00002", "customer_id": "CUST-002", "amount": 250.00, "status": "completed", "date": "2025-11-21"},
        {"id": "TXN-00003", "customer_id": "CUST-001", "amount": 75.00, "status": "pending", "date": "2025-11-22"},
    ],
    "orders": [
        {"id": "ORD-001", "customer_id": "CUST-001", "product": "Laptop", "status": "shipped"},
        {"id": "ORD-002", "customer_id": "CUST-002", "product": "Phone", "status": "delivered"},
    ]
}

# Mock Vector Database (FAISS simulation)
MOCK_KNOWLEDGE_BASE = [
    "Our refund policy allows refunds within 30 days of purchase for most items.",
    "Premium customers get free shipping on all orders over $50.",
    "We use secure payment processing through Stripe and PayPal.",
    "Customer data is encrypted using AES-256 encryption.",
    "Our support hours are Monday-Friday 9AM-5PM EST.",
    "Order tracking is available 24 hours after shipment.",
    "International shipping takes 7-14 business days.",
    "Return labels can be generated from your account dashboard.",
]


def fetch_customer_balance(customer_id: str) -> Dict:
    """
    Fetch customer balance from the database.
    
    Args:
        customer_id: Customer ID in format CUST-XXX
    
    Returns:
        Dictionary with customer balance information
    """
    for customer in MOCK_DATABASE["customers"]:
        if customer["id"] == customer_id:
            return {
                "customer_id": customer_id,
                "name": customer["name"],
                "balance": customer["balance"],
                "status": "active"
            }
    
    return {"error": f"Customer {customer_id} not found"}


def process_refund_transaction(transaction_id: str, amount: float, reason: str = "customer_request") -> Dict:
    """
    Process a refund for a transaction.
    
    AUTHORIZATION RULES:
    - Refunds under $1000 are auto-approved
    - Refunds $1000 or more require manager approval
    - Transaction ID must follow format TXN-XXXXX (exactly 9 characters)
    - Amount must be positive and not exceed original transaction
    
    Args:
        transaction_id: Transaction ID in format TXN-XXXXX
        amount: Refund amount in USD
        reason: Reason for refund
    
    Returns:
        Dictionary with refund status
    """
    # Validation: Check transaction ID format
    if not transaction_id.startswith("TXN-") or len(transaction_id) != 9:
        return {
            "error": "Invalid transaction ID format. Must be TXN-XXXXX (9 characters total)",
            "transaction_id": transaction_id
        }
    
    # Validation: Amount must be positive
    if amount <= 0:
        return {"error": "Refund amount must be positive"}
    
    # Find transaction
    transaction = None
    for txn in MOCK_DATABASE["transactions"]:
        if txn["id"] == transaction_id:
            transaction = txn
            break
    
    if not transaction:
        return {"error": f"Transaction {transaction_id} not found"}
    
    # Validation: Amount cannot exceed original
    if amount > transaction["amount"]:
        return {"error": f"Refund amount ${amount} exceeds original transaction ${transaction['amount']}"}
    
    # Authorization check: Manager approval for large refunds
    if amount >= 1000:
        return {
            "status": "pending_approval",
            "transaction_id": transaction_id,
            "amount": amount,
            "reason": reason,
            "message": "Refund requires manager approval (amount >= $1000)",
            "approval_required": True
        }
    
    # Auto-approve small refunds
    return {
        "status": "approved",
        "transaction_id": transaction_id,
        "amount": amount,
        "refund_id": f"REF-{random.randint(10000, 99999)}",
        "processed_at": datetime.utcnow().isoformat(),
        "estimated_arrival": (datetime.utcnow() + timedelta(days=5)).strftime("%Y-%m-%d")
    }


def query_order_status(order_id: str) -> Dict:
    """
    Query the status of an order.
    
    Args:
        order_id: Order ID in format ORD-XXX
    
    Returns:
        Dictionary with order status
    """
    for order in MOCK_DATABASE["orders"]:
        if order["id"] == order_id:
            return {
                "order_id": order_id,
                "product": order["product"],
                "status": order["status"],
                "customer_id": order["customer_id"]
            }
    
    return {"error": f"Order {order_id} not found"}


def search_knowledge_base(query: str, top_k: int = 3) -> List[str]:
    """
    Search the vector database (FAISS) for relevant information.
    
    Uses semantic search to find most relevant documents.
    Infrastructure: FAISS vector store with OpenAI text-embedding-3-small embeddings
    
    Args:
        query: Search query
        top_k: Number of results to return (default: 3)
    
    Returns:
        List of relevant knowledge base entries
    """
    # Simple keyword-based search (mock semantic search)
    query_lower = query.lower()
    scored_docs = []
    
    for doc in MOCK_KNOWLEDGE_BASE:
        doc_lower = doc.lower()
        # Simple scoring: count matching words
        score = sum(1 for word in query_lower.split() if word in doc_lower)
        if score > 0:
            scored_docs.append((score, doc))
    
    # Sort by score and return top_k
    scored_docs.sort(reverse=True, key=lambda x: x[0])
    return [doc for _, doc in scored_docs[:top_k]]


def get_transaction_history(customer_id: str, limit: int = 10) -> List[Dict]:
    """
    Get transaction history for a customer.
    
    Args:
        customer_id: Customer ID in format CUST-XXX
        limit: Maximum number of transactions to return
    
    Returns:
        List of transaction dictionaries
    """
    transactions = [
        txn for txn in MOCK_DATABASE["transactions"]
        if txn["customer_id"] == customer_id
    ]
    
    return transactions[:limit]


# Tool registry for easy access
AVAILABLE_TOOLS = {
    "fetch_customer_balance": fetch_customer_balance,
    "process_refund_transaction": process_refund_transaction,
    "query_order_status": query_order_status,
    "search_knowledge_base": search_knowledge_base,
    "get_transaction_history": get_transaction_history,
}
