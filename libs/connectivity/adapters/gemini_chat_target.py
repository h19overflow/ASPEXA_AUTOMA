"""
Gemini Chat Target for PyRIT.

Implements PyRIT's PromptChatTarget interface using Google's Gemini API.
Allows using GOOGLE_API_KEY instead of OpenAI credentials.

Uses langchain-google-genai for Gemini access (already in project dependencies).
"""
import logging
import os
from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from pyrit.models import PromptRequestPiece, PromptRequestResponse
from pyrit.prompt_target import PromptChatTarget

logger = logging.getLogger(__name__)


class GeminiChatTarget(PromptChatTarget):
    """
    PyRIT PromptChatTarget implementation for Google Gemini.

    Uses GOOGLE_API_KEY environment variable for authentication.
    Wraps LangChain's ChatGoogleGenerativeAI for API access.
    """

    def __init__(
        self,
        model_name: str = "gemini-2.0-flash",
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ):
        """
        Initialize Gemini chat target.

        Args:
            model_name: Gemini model to use
            api_key: Google API key (defaults to GOOGLE_API_KEY env var)
            temperature: Sampling temperature
            max_tokens: Maximum output tokens
        """
        super().__init__()

        self._api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not self._api_key:
            raise ValueError(
                "GOOGLE_API_KEY environment variable must be set or api_key provided"
            )

        self._model_name = model_name
        self._temperature = temperature
        self._max_tokens = max_tokens

        # Use LangChain's Gemini wrapper
        self._llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=self._api_key,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        logger.info(f"GeminiChatTarget initialized with model: {model_name}")

    async def send_prompt_async(
        self, *, prompt_request: PromptRequestResponse
    ) -> PromptRequestResponse:
        """
        Send prompt to Gemini and return response.

        Args:
            prompt_request: PyRIT prompt request containing the prompt pieces

        Returns:
            PromptRequestResponse with Gemini's response
        """
        self._validate_request(prompt_request=prompt_request)

        request_pieces = prompt_request.request_pieces
        prompt_text = self._get_prompt_text(request_pieces)

        try:
            # Build conversation history if available
            conversation_id = request_pieces[0].conversation_id
            messages = await self._build_langchain_messages(conversation_id, prompt_text)

            # Use LangChain's async invoke
            response = await self._llm.ainvoke(messages)
            response_text = response.content

            logger.debug(f"Gemini response: {response_text[:100]}...")

            return self._create_response(
                request_pieces=request_pieces,
                response_text=response_text,
            )

        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return self._create_response(
                request_pieces=request_pieces,
                response_text=f"Error: {str(e)}",
                error=str(e),
            )

    def _validate_request(self, *, prompt_request: PromptRequestResponse) -> None:
        """Validate the prompt request."""
        if not prompt_request.request_pieces:
            raise ValueError("No request pieces in prompt_request")

        for piece in prompt_request.request_pieces:
            if piece.converted_value_data_type != "text":
                raise ValueError(
                    f"GeminiChatTarget only supports text prompts, "
                    f"got: {piece.converted_value_data_type}"
                )

    def _get_prompt_text(self, request_pieces: list[PromptRequestPiece]) -> str:
        """Extract prompt text from request pieces."""
        # Use converted_value if available, otherwise original_value
        piece = request_pieces[0]
        return piece.converted_value or piece.original_value or ""

    async def _build_langchain_messages(
        self, conversation_id: str, current_prompt: str
    ) -> list:
        """
        Build LangChain message list from PyRIT memory.

        Args:
            conversation_id: Conversation ID to retrieve history for
            current_prompt: The current user prompt to send

        Returns:
            List of LangChain messages (HumanMessage, AIMessage)
        """
        from langchain_core.messages import HumanMessage, AIMessage

        messages = []

        try:
            from pyrit.memory import CentralMemory
            memory = CentralMemory.get_memory_instance()

            # Get previous turns in this conversation
            entries = memory.get_prompt_request_pieces(conversation_id=conversation_id)

            for entry in entries:
                content = entry.converted_value or entry.original_value
                if entry.role == "user":
                    messages.append(HumanMessage(content=content))
                elif entry.role == "assistant":
                    messages.append(AIMessage(content=content))

        except Exception as e:
            logger.debug(f"Could not retrieve conversation history: {e}")

        # Add current prompt
        messages.append(HumanMessage(content=current_prompt))
        return messages

    def _create_response(
        self,
        request_pieces: list[PromptRequestPiece],
        response_text: str,
        error: Optional[str] = None,
    ) -> PromptRequestResponse:
        """Create PyRIT response from Gemini output."""
        response_piece = PromptRequestPiece(
            role="assistant",
            original_value=response_text,
            converted_value=response_text,
            converted_value_data_type="text",
            conversation_id=request_pieces[0].conversation_id,
            sequence=request_pieces[0].sequence + 1,
            prompt_target_identifier=self.get_identifier(),
        )

        if error:
            response_piece.response_error = error

        return PromptRequestResponse(request_pieces=[response_piece])

    def is_json_response_supported(self) -> bool:
        """
        Check if JSON response mode is supported.

        Returns:
            False - Gemini via LangChain doesn't have structured JSON mode.
        """
        return False

    def get_identifier(self) -> dict:
        """Return target identifier for logging."""
        return {
            "__type__": "GeminiChatTarget",
            "model_name": self._model_name,
        }
