from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from vector_store import search_similar_chunks, get_total_chunks, deduplicate_by_posting
from llm_service import ask_gpt

router = APIRouter()
templates = Jinja2Templates(directory="templates")

_SYSTEM_PROMPT = """\
You are a helpful career advisor specializing in the Pakistani tech job market.
You have access to job posting excerpts provided as context.
Answer the user's question based strictly on the provided context.
Be specific, practical, and insightful. When writing cover letters or similar
content, tailor them to the Pakistani market. Keep answers concise but thorough.\
"""


@router.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="search.html",
        context={"has_postings": get_total_chunks() > 0},
    )


@router.post("/search", response_class=HTMLResponse)
async def search_query(request: Request, query: str = Form(...)):
    answer = None
    sources = []
    error = None
    insight_note = None

    try:
        raw_chunks = search_similar_chunks(query, n_results=6)

        if not raw_chunks:
            error = "No job postings found in the database. Please upload some postings first."
        else:
            unique_sources = deduplicate_by_posting(raw_chunks)
            n = len(unique_sources)
            insight_note = (
                "Insights are based on a single posting."
                if n == 1
                else f"Insights aggregated from {n} postings."
            )

            context_parts = [
                f"[Source {i}: {c['metadata']['company_name']} — {c['metadata']['role_title']}]\n{c['document']}"
                for i, c in enumerate(unique_sources, 1)
            ]
            context = "\n\n---\n\n".join(context_parts)

            user_message = (
                f"Context from job postings:\n\n{context}\n\n"
                f"Question: {query}\n\n"
                "Please answer based on the provided job posting excerpts."
            )

            answer = ask_gpt(_SYSTEM_PROMPT, user_message)
            sources = unique_sources

    except Exception as exc:
        error = f"Search failed: {exc}"

    return templates.TemplateResponse(
        request=request,
        name="search.html",
        context={
            "query": query,
            "answer": answer,
            "sources": sources,
            "error": error,
            "has_postings": True,
            "insight_note": insight_note,
        },
    )
