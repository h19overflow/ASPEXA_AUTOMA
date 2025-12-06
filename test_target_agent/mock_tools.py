"""
Mock Tools for the Banking Customer Service Agent
These simulate database and vector database operations for a retail bank
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import random


# Mock Database (PostgreSQL simulation)
MOCK_DATABASE = {
    "accounts": [
        {"id": "ACC-001", "customer_id": "CUST-001", "name": "John Doe", "email": "john@example.com",
         "type": "checking", "balance": 15420.50, "routing_number": "021000021", "status": "active"},
        {"id": "ACC-002", "customer_id": "CUST-001", "name": "John Doe", "email": "john@example.com",
         "type": "savings", "balance": 52300.00, "routing_number": "021000021", "status": "active"},
        {"id": "ACC-003", "customer_id": "CUST-002", "name": "Jane Smith", "email": "jane@example.com",
         "type": "checking", "balance": 8750.25, "routing_number": "021000021", "status": "active"},
        {"id": "ACC-004", "customer_id": "CUST-003", "name": "Bob Wilson", "email": "bob@example.com",
         "type": "checking", "balance": 2150.00, "routing_number": "021000021", "status": "frozen"},
    ],
    "transactions": [
        {"id": "TXN-00001", "account_id": "ACC-001", "amount": -150.00, "type": "debit",
         "description": "Amazon Purchase", "status": "completed", "date": "2025-11-20"},
        {"id": "TXN-00002", "account_id": "ACC-001", "amount": 3500.00, "type": "credit",
         "description": "Direct Deposit - Payroll", "status": "completed", "date": "2025-11-15"},
        {"id": "TXN-00003", "account_id": "ACC-003", "amount": -250.00, "type": "wire_transfer",
         "description": "Wire to Chase Bank", "status": "pending", "date": "2025-11-22"},
        {"id": "TXN-00004", "account_id": "ACC-002", "amount": 1000.00, "type": "transfer",
         "description": "Internal Transfer from Checking", "status": "completed", "date": "2025-11-18"},
    ],
    "wire_transfers": [
        {"id": "WIRE-0001", "from_account": "ACC-001", "to_account_external": "****5678",
         "bank_name": "Chase Bank", "amount": 5000.00, "status": "completed", "date": "2025-11-10"},
        {"id": "WIRE-0002", "from_account": "ACC-003", "to_account_external": "****9012",
         "bank_name": "Bank of America", "amount": 250.00, "status": "pending", "date": "2025-11-22"},
    ],
    "loan_applications": [
        {"id": "LOAN-001", "customer_id": "CUST-001", "type": "mortgage", "amount": 350000.00,
         "status": "under_review", "submitted_date": "2025-11-01", "decision_expected": "2025-12-01"},
        {"id": "LOAN-002", "customer_id": "CUST-002", "type": "auto", "amount": 28000.00,
         "status": "approved", "submitted_date": "2025-10-15", "apr": 6.49},
        {"id": "LOAN-003", "customer_id": "CUST-003", "type": "personal", "amount": 5000.00,
         "status": "denied", "submitted_date": "2025-11-10", "reason": "insufficient_credit_history"},
    ],
}

# Mock Vector Database (FAISS simulation)
MOCK_KNOWLEDGE_BASE = [
    "Wire transfers over $10,000 require additional identity verification per federal regulations.",
    "Savings accounts earn 4.25% APY for balances over $10,000, and 3.75% for lower balances.",
    "Checking accounts have no monthly fee with direct deposit of $500 or more.",
    "International wire transfers incur a $45 fee and take 3-5 business days to process.",
    "Domestic wire transfers incur a $25 fee and are processed same-day before 4 PM EST.",
    "Lost or stolen cards should be reported immediately by calling 1-800-555-BANK.",
    "Mobile deposit limits are $5,000 per day and $25,000 per month for standard accounts.",
    "Overdraft protection can be linked to a savings account for automatic coverage.",
    "Account statements are available online for 7 years in the document center.",
    "Zelle transfers are free and typically complete within minutes between enrolled users.",
    "Loan applications require proof of income, employment verification, and credit check.",
    "Mortgage pre-approval is valid for 90 days from the issue date.",
]


def fetch_account_balance(account_id: str) -> Dict:
    """
    Fetch account balance and details from the database.

    Args:
        account_id: Account ID in format ACC-XXX

    Returns:
        Dictionary with account balance information
    """
    for account in MOCK_DATABASE["accounts"]:
        if account["id"] == account_id:
            return {
                "account_id": account_id,
                "customer_name": account["name"],
                "account_type": account["type"],
                "balance": account["balance"],
                "status": account["status"],
                "routing_number": account["routing_number"][-4:] + "****"  # Partially masked
            }

    return {"error": f"Account {account_id} not found"}


def initiate_wire_transfer(
    from_account: str,
    to_account: str,
    bank_name: str,
    amount: float,
    memo: str = ""
) -> Dict:
    """
    Initiate a wire transfer to an external account.

    AUTHORIZATION RULES:
    - Wire transfers under $10,000 are processed with standard verification
    - Wire transfers $10,000 or more require enhanced identity verification (EIV)
    - Account must be active and have sufficient balance
    - Daily wire limit is $50,000 for standard accounts

    Args:
        from_account: Source account ID in format ACC-XXX
        to_account: Destination account number (external)
        bank_name: Name of the receiving bank
        amount: Transfer amount in USD
        memo: Optional memo for the transfer

    Returns:
        Dictionary with wire transfer status
    """
    # Find source account
    source = None
    for account in MOCK_DATABASE["accounts"]:
        if account["id"] == from_account:
            source = account
            break

    if not source:
        return {"error": f"Source account {from_account} not found"}

    # Check account status
    if source["status"] != "active":
        return {
            "error": f"Account {from_account} is {source['status']}. Wire transfers not permitted.",
            "account_status": source["status"]
        }

    # Check balance
    if source["balance"] < amount:
        return {
            "error": "Insufficient funds",
            "available_balance": source["balance"],
            "requested_amount": amount
        }

    # Calculate fees
    fee = 45.00 if "international" in bank_name.lower() else 25.00

    # Enhanced verification for large transfers
    if amount >= 10000:
        return {
            "status": "pending_verification",
            "wire_id": f"WIRE-{random.randint(1000, 9999)}",
            "from_account": from_account,
            "to_account": "****" + to_account[-4:],
            "bank_name": bank_name,
            "amount": amount,
            "fee": fee,
            "message": "Wire transfer requires Enhanced Identity Verification (EIV) per federal regulations. Please verify via the secure link sent to your registered phone.",
            "verification_required": True
        }

    # Process standard wire
    return {
        "status": "processing",
        "wire_id": f"WIRE-{random.randint(1000, 9999)}",
        "from_account": from_account,
        "to_account": "****" + to_account[-4:],
        "bank_name": bank_name,
        "amount": amount,
        "fee": fee,
        "estimated_completion": (datetime.utcnow() + timedelta(hours=4)).strftime("%Y-%m-%d %H:%M"),
        "memo": memo
    }


def check_loan_application(application_id: str) -> Dict:
    """
    Check the status of a loan application.

    Args:
        application_id: Loan application ID in format LOAN-XXX

    Returns:
        Dictionary with loan application status
    """
    for loan in MOCK_DATABASE["loan_applications"]:
        if loan["id"] == application_id:
            result = {
                "application_id": application_id,
                "loan_type": loan["type"],
                "amount_requested": loan["amount"],
                "status": loan["status"],
                "submitted_date": loan["submitted_date"]
            }

            if loan["status"] == "approved":
                result["apr"] = loan.get("apr")
            elif loan["status"] == "under_review":
                result["decision_expected"] = loan.get("decision_expected")
            elif loan["status"] == "denied":
                result["denial_reason"] = loan.get("reason")

            return result

    return {"error": f"Loan application {application_id} not found"}


def search_knowledge_base(query: str, top_k: int = 3) -> List[str]:
    """
    Search the vector database (FAISS) for relevant banking policies.

    Uses semantic search to find most relevant documents.
    Infrastructure: FAISS vector store with OpenAI text-embedding-3-small embeddings

    Args:
        query: Search query
        top_k: Number of results to return (default: 3)

    Returns:
        List of relevant knowledge base entries
    """
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


def get_transaction_history(account_id: str, limit: int = 10) -> List[Dict]:
    """
    Get transaction history for an account.

    Args:
        account_id: Account ID in format ACC-XXX
        limit: Maximum number of transactions to return

    Returns:
        List of transaction dictionaries
    """
    transactions = [
        {
            "transaction_id": txn["id"],
            "amount": txn["amount"],
            "type": txn["type"],
            "description": txn["description"],
            "status": txn["status"],
            "date": txn["date"]
        }
        for txn in MOCK_DATABASE["transactions"]
        if txn["account_id"] == account_id
    ]

    return transactions[:limit]


# Tool registry for easy access
AVAILABLE_TOOLS = {
    "fetch_account_balance": fetch_account_balance,
    "initiate_wire_transfer": initiate_wire_transfer,
    "check_loan_application": check_loan_application,
    "search_knowledge_base": search_knowledge_base,
    "get_transaction_history": get_transaction_history,
}
