# Onboarding & Contributor Guide

Welcome to Aspexa Automa! This guide will help you set up your development environment and understand how to contribute to the project.

---

## 1. Development Setup

### Prerequisites
- **Python 3.12+**
- **uv** (Recommended package manager)
- **PostgreSQL** (Local or Docker)
- **Google AI API Key** (For Gemini 1.5 Flash)

### Steps
1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/your-org/aspexa-automa.git
    cd aspexa-automa
    ```

2.  **Install Dependencies**:
    ```bash
    uv sync
    ```

3.  **Configure Environment**:
    Create a `.env` file in the root directory:
    ```env
    GOOGLE_API_KEY=your_gemini_key_here
    DATABASE_URL=postgresql+asyncpg://user:pass@localhost/aspexa
    CLERK_SECRET_KEY=your_clerk_key_here  # Optional for local dev
    ```

4.  **Run Migrations / Setup DB**:
    Ensure PostgreSQL is running and your user has permissions to create databases.

5.  **Start the API Gateway**:
    ```bash
    python -m services.api_gateway.main
    ```

---

## 2. Project Architecture Refresher

Before contributing, please read:
- **[System Overview](main.md)**: High-level philosophy and pipeline.
- **[Code Base Structure](code_base_structure.md)**: Where to find what.
- **[API Architecture](api_architecture.md)**: How services communicate.

---

## 3. Contribution Workflow

### Code Standards
- **Async First**: Use `async/await` for all I/O bound operations.
- **Type Hints**: Mandatory for all public functions and class members.
- **Testing**: Every new feature must include unit tests. Aim for >60% coverage.
- **Style**: We use `ruff` for linting and formatting. Run `ruff check .` before committing.

### Development Process
1.  **Create a Branch**: `feat/your-feature-name` or `fix/issue-id`.
2.  **Implement & Test**: Write your code and ensure `pytest` passes.
3.  **Documentation**: Update relevant `.md` files in `docs/` if you change architecture or contracts.
4.  **Pull Request**: Submit a PR with a clear description of your changes.

---

## 4. Key Components to Explore

- **`libs/contracts/`**: The "source of truth" for service interfaces.
- **`services/cartographer/`**: The LangGraph-based reconnaissance agent.
- **`services/swarm/`**: The Trinity agents and Garak scanner integration.
- **`services/snipers/`**: The PyRIT exploitation workflow.

---

## 5. Useful Commands

| Command | Purpose |
|---------|---------|
| `uv sync` | Install/update dependencies |
| `pytest` | Run all tests |
| `ruff check .` | Lint the codebase |
| `python -m services.api_gateway.main` | Start the local API gateway |

---

## Need Help?
If you're stuck, please check the [existing issues](https://github.com/your-org/aspexa-automa/issues) or reach out to the project maintainers.
