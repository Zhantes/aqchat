import time
from threading import Lock
from typing import Dict, List, Iterator
from langchain_core.messages.base import BaseMessageChunk
from langchain_core.messages import AIMessageChunk
from pipelines.abstract_chat import AbstractChatPipeline
from pipelines.abstract_memory import AbstractMemoryPipeline


class TestingChatPipeline(AbstractChatPipeline):
    """Testing chat implementation that simulates streaming LLM responses.
    
    This class simulates a streaming LLM response with a thinking section followed by
    the main response. It's deterministic to support unit testing and doesn't require
    any external services.
    
    NOTE: This class MUST be thread-safe as streamlit runs multiple worker threads
    and the pipeline for a given repo will be cached, meaning several users
    having sessions may result in concurrent accesses.
    """
    
    # --------------------------------------------------------------
    # INITIALISATION
    # --------------------------------------------------------------
    
    def __init__(
        self,
        memory: AbstractMemoryPipeline = None,
        *,
        response_delay: float = 0.1,
        token_delay: float = 0.05,
        thinking_delay: float = 0.03,
        use_context: bool = True,
    ) -> None:
        """Initialize the testing chat pipeline.
        
        Args:
            response_delay: Delay before starting response (seconds)
            token_delay: Delay between tokens (seconds)
            thinking_delay: Delay between thinking tokens (seconds)
            use_context: Whether to incorporate retrieved context in responses
        """
        # allocate mutex
        self.lock = Lock()

        self.memory = memory
        
        # Configuration for response simulation
        self.response_delay = response_delay
        self.token_delay = token_delay
        self.thinking_delay = thinking_delay
        self.use_context = use_context
    
    def query(self, messages: List[Dict[str, str]]) -> Iterator[BaseMessageChunk]:
        """Stream a simulated answer for *messages*.
        
        ``messages`` must be a list of chat messages of the form
        ``[{"role": "user" | "assistant" | "system", "content": "..."}, ...]``.
        The final user message is treated as the question for retrieval.
        """
        with self.lock:
            if not self.memory.ready_for_retrieval():
                raise RuntimeError("Call .ingest(<path>) before querying.")
            
            question = self._extract_latest_user_message(messages)
            if question is None:
                raise ValueError("No user message found in conversation history.")
            
            # Simulate initial processing delay
            time.sleep(self.response_delay)
            
            # Generate thinking section
            thinking_text = self._generate_thinking_section(question)
            
            # Generate main response
            if self.use_context:
                # Retrieve relevant context for the *current* question only
                docs = self.memory.invoke(question)
                context = "\n\n".join(d.page_content for d in docs)
                response_text = self._generate_contextual_response(question, context)
            else:
                response_text = self._generate_simple_response(question)
            
            # Stream thinking section first
            yield from self._stream_thinking(thinking_text)
            
            # Stream the main response
            yield from self._stream_response(response_text)
    
    def _extract_latest_user_message(self, messages: List[Dict[str, str]]) -> str | None:
        """Return the content of the *most recent* user message, or ``None``."""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                return msg.get("content", "")
        return None
    
    def _generate_thinking_section(self, question: str) -> str:
        """Generate a deterministic thinking section based on the question."""
        return f"""<think>
The user is asking: "{question[:100]}{'...' if len(question) > 100 else ''}"

I need to:
1. Analyze the question to understand what information is being requested
2. Look at the retrieved context to find relevant information
3. Structure a clear and helpful response that addresses the question directly
4. Ensure my response is based on the provided context when available

Let me examine the context and formulate an appropriate response.
</think>

"""
    
    def _generate_contextual_response(self, question: str, context: str) -> str:
        """Generate a deterministic response that incorporates the retrieved context."""
        context_preview = context[:200] + "..." if len(context) > 200 else context
        
        response = f"""Based on the provided context, I can help answer your question about "{question[:50]}{'...' if len(question) > 50 else ''}".

The relevant information from the context includes:

{context_preview}

This information directly relates to your question and provides the foundation for a comprehensive answer. The context contains specific details that allow me to give you an accurate and well-informed response.

To summarize: the context provides clear guidance on this topic, and I've used that information to address your specific question as thoroughly as possible."""
        
        return response
    
    def _generate_simple_response(self, question: str) -> str:
        """Generate a deterministic simple response without context."""
        return f"""I understand you're asking about "{question[:50]}{'...' if len(question) > 50 else ''}".

This is a simulated response for testing purposes. In a real scenario, I would use the retrieved context from your documents to provide specific and accurate information relevant to your question.

The testing pipeline is working correctly and can process your question, but it's generating this placeholder response instead of using an actual language model."""
    
    def _stream_thinking(self, thinking_text: str) -> Iterator[BaseMessageChunk]:
        """Stream the thinking section with faster timing."""
        tokens = self._tokenize_text(thinking_text)
        
        for token in tokens:
            chunk = AIMessageChunk(content=token)
            time.sleep(self.thinking_delay)
            yield chunk
    
    def _stream_response(self, response_text: str) -> Iterator[BaseMessageChunk]:
        """Stream the response text token by token with realistic timing."""
        tokens = self._tokenize_text(response_text)
        
        for i, token in enumerate(tokens):
            chunk = AIMessageChunk(content=token)
            
            # Add delay between tokens, with longer delays after punctuation
            if i > 0:
                if tokens[i-1].rstrip().endswith(('.', '!', '?', ':')):
                    time.sleep(self.token_delay * 2)  # Longer pause after punctuation
                else:
                    time.sleep(self.token_delay)
            
            yield chunk
    
    def _tokenize_text(self, text: str) -> List[str]:
        """Simple tokenization that splits text into words while preserving formatting."""
        # Split on spaces but preserve line breaks and structure
        lines = text.split('\n')
        tokens = []
        
        for i, line in enumerate(lines):
            if line.strip():  # Non-empty line
                words = line.split()
                for j, word in enumerate(words):
                    if j == 0:
                        tokens.append(word)
                    else:
                        tokens.append(' ' + word)
            
            # Add line break except for the last line
            if i < len(lines) - 1:
                tokens.append('\n')
        
        return tokens