from openai import OpenAI, AuthenticationError, RateLimitError, APIConnectionError, APIError
from dotenv import load_dotenv
from typing import List
import os

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

EMBEDDING_MODEL = "text-embedding-ada-002"
CHAT_MODEL = "gpt-4o-mini"


def _wrap_openai_error(exc: Exception) -> Exception:
    if isinstance(exc, AuthenticationError):
        return ValueError("Invalid OpenAI API key. Please check your OPENAI_API_KEY in .env.")
    if isinstance(exc, RateLimitError):
        return ValueError("OpenAI rate limit reached. Please wait a moment and try again.")
    if isinstance(exc, APIConnectionError):
        return ValueError("Could not connect to OpenAI. Check your internet connection.")
    if isinstance(exc, APIError):
        return ValueError(f"OpenAI API error: {exc.message}")
    return exc


def get_embedding(text: str) -> List[float]:
    try:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text.replace("\n", " "),
        )
        return response.data[0].embedding
    except Exception as exc:
        raise _wrap_openai_error(exc) from exc


def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    try:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=[t.replace("\n", " ") for t in texts],
        )
        return [item.embedding for item in response.data]
    except Exception as exc:
        raise _wrap_openai_error(exc) from exc


def ask_gpt(system_prompt: str, user_message: str, max_tokens: int = 1500) -> str:
    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
    except Exception as exc:
        raise _wrap_openai_error(exc) from exc
