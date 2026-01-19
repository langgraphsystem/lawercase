"""
EB-1A RAG Examples Retrieval.

This module provides functions to retrieve relevant examples from the
Supabase vector store for use during criteria evaluation.
"""

from __future__ import annotations

from typing import Any

from ...storage.supabase_vector_store import SupabaseVectorStore
from .criteria_skill import CriterionType

# Namespace for EB-1A examples
EB1A_EXAMPLES_NAMESPACE = "eb1a_petition_examples"

# Criterion type to tag mapping
CRITERION_TAG_MAP = {
    CriterionType.AWARDS: "criterion:awards",
    CriterionType.MEMBERSHIP: "criterion:membership",
    CriterionType.PUBLISHED_MATERIAL: "criterion:published_material",
    CriterionType.JUDGING: "criterion:judging",
    CriterionType.ORIGINAL_CONTRIBUTIONS: "criterion:original_contributions",
    CriterionType.SCHOLARLY_ARTICLES: "criterion:scholarly_articles",
    CriterionType.EXHIBITIONS: "criterion:exhibitions",
    CriterionType.LEADING_ROLE: "criterion:leading_role",
    CriterionType.HIGH_SALARY: "criterion:high_salary",
    CriterionType.COMMERCIAL_SUCCESS: "criterion:commercial_success",
    CriterionType.COMPARABLE_EVIDENCE: "criterion:comparable_evidence",
}


async def get_relevant_examples(
    query: str,
    criterion: CriterionType | None = None,
    field: str | None = None,
    topk: int = 3,
    min_score: float = 0.4,
) -> list[dict[str, Any]]:
    """
    Retrieve relevant examples from the RAG store.

    Args:
        query: Search query (e.g., description of evidence to evaluate)
        criterion: Optional filter by specific criterion
        field: Optional filter by field (e.g., "education", "technology")
        topk: Maximum number of examples to return
        min_score: Minimum similarity score threshold

    Returns:
        List of relevant examples with metadata
    """
    try:
        # Import embedder lazily to avoid circular imports
        from ...llm.supabase_embedder import get_embedder

        # Get embedder and generate query embedding
        embedder = get_embedder()
        query_embedding = (await embedder.embed_texts([query]))[0]

        # Build filters
        filters: dict[str, Any] = {}
        if criterion and criterion in CRITERION_TAG_MAP:
            filters["tags"] = [CRITERION_TAG_MAP[criterion]]

        # Initialize vector store
        store = SupabaseVectorStore(namespace=EB1A_EXAMPLES_NAMESPACE)

        # Search for similar examples
        results = await store.search(
            query_embedding,
            topk=topk,
            filters=filters,
            min_score=min_score,
        )

        # Format results
        examples = []
        for result in results:
            metadata = result.get("metadata", {})
            examples.append(
                {
                    "id": result.get("record_id"),
                    "score": result.get("score", 0.0),
                    "title": metadata.get("title", "Unknown"),
                    "criterion": metadata.get("criterion"),
                    "field": metadata.get("field"),
                    "summary": metadata.get("summary", ""),
                    "text": metadata.get("text", ""),
                    "key_elements": metadata.get("key_elements", []),
                    "required_documents": metadata.get("required_documents", []),
                }
            )

        return examples

    except Exception as e:
        # Log error but don't fail the evaluation
        import logging

        logging.warning(f"Failed to retrieve RAG examples: {e}")
        return []


async def get_examples_for_criterion(
    criterion: CriterionType,
    case_summary: str | None = None,
    topk: int = 2,
) -> list[dict[str, Any]]:
    """
    Get example cases for a specific criterion.

    Args:
        criterion: The EB-1A criterion to get examples for
        case_summary: Optional case summary to find most relevant examples
        topk: Number of examples to return

    Returns:
        List of example cases with metadata
    """
    # Build search query based on criterion and case summary
    criterion_descriptions = {
        CriterionType.AWARDS: "awards prizes recognition excellence",
        CriterionType.MEMBERSHIP: "membership association professional organization",
        CriterionType.PUBLISHED_MATERIAL: "published media article interview coverage",
        CriterionType.JUDGING: "judge panel review evaluate competition",
        CriterionType.ORIGINAL_CONTRIBUTIONS: "original contribution innovation significant impact",
        CriterionType.SCHOLARLY_ARTICLES: "scholarly article publication journal paper",
        CriterionType.EXHIBITIONS: "exhibition showcase display presentation",
        CriterionType.LEADING_ROLE: "leading critical role organization distinguished",
        CriterionType.HIGH_SALARY: "high salary remuneration compensation",
        CriterionType.COMMERCIAL_SUCCESS: "commercial success sales revenue performing arts",
        CriterionType.COMPARABLE_EVIDENCE: "comparable evidence alternative criteria",
    }

    query = criterion_descriptions.get(criterion, "EB-1A criteria evidence")

    if case_summary:
        query = f"{query} {case_summary[:200]}"

    return await get_relevant_examples(
        query=query,
        criterion=criterion,
        topk=topk,
        min_score=0.3,
    )


def format_examples_for_prompt(examples: list[dict[str, Any]]) -> str:
    """
    Format retrieved examples for inclusion in evaluation prompts.

    Args:
        examples: List of examples from RAG

    Returns:
        Formatted string for prompt inclusion
    """
    if not examples:
        return "No similar examples found in the knowledge base."

    sections = ["## Reference Examples from Approved Petitions\n"]

    for i, ex in enumerate(examples, 1):
        sections.append(f"### Example {i}: {ex.get('title', 'Untitled')}")
        sections.append(f"**Field:** {ex.get('field', 'N/A')}")
        sections.append(f"**Relevance Score:** {ex.get('score', 0):.2f}")

        if summary := ex.get("summary"):
            sections.append(f"**Summary:** {summary}")

        if key_elements := ex.get("key_elements"):
            sections.append("**Key Elements:**")
            for elem in key_elements:
                sections.append(f"  - {elem}")

        if required_docs := ex.get("required_documents"):
            sections.append("**Required Documentation:**")
            for doc in required_docs:
                sections.append(f"  - {doc}")

        sections.append("")  # Blank line between examples

    return "\n".join(sections)


async def enrich_prompt_with_examples(
    base_prompt: str,
    criterion: CriterionType,
    case_context: dict[str, Any],
) -> str:
    """
    Enrich an evaluation prompt with relevant examples from RAG.

    Args:
        base_prompt: The base evaluation prompt
        criterion: The criterion being evaluated
        case_context: Case context for finding relevant examples

    Returns:
        Enriched prompt with examples included
    """
    # Build case summary from context
    case_summary_parts = []
    if field := case_context.get("field_of_expertise"):
        case_summary_parts.append(f"Field: {field}")
    if specialty := case_context.get("specialty"):
        case_summary_parts.append(f"Specialty: {specialty}")

    case_summary = " ".join(case_summary_parts) if case_summary_parts else None

    # Get relevant examples
    examples = await get_examples_for_criterion(
        criterion=criterion,
        case_summary=case_summary,
        topk=2,
    )

    if not examples:
        return base_prompt

    # Format examples and add to prompt
    examples_section = format_examples_for_prompt(examples)

    # Insert examples before the "Evidence to Evaluate" section
    if "## Evidence to Evaluate:" in base_prompt:
        return base_prompt.replace(
            "## Evidence to Evaluate:",
            f"{examples_section}\n## Evidence to Evaluate:",
        )

    # Otherwise append at the end
    return f"{base_prompt}\n\n{examples_section}"


__all__ = [
    "EB1A_EXAMPLES_NAMESPACE",
    "enrich_prompt_with_examples",
    "format_examples_for_prompt",
    "get_examples_for_criterion",
    "get_relevant_examples",
]
