"""LangGraph nodes wrapping EB-1A PDF pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog

from config.settings import get_settings
from core.orchestration.workflow_graph import WorkflowState
from recommendation_pipeline.document_generator import generate_document
from recommendation_pipeline.index_builder import build_index
from recommendation_pipeline.ocr_runner import analyze_images, finalize_pdf
from recommendation_pipeline.pdf_assembler import assemble_master_pdf
from recommendation_pipeline.pdf_finalize import finalize_master_pdf
from recommendation_pipeline.schemas.exhibits import DocGenRequest

logger = structlog.get_logger(__name__)

try:  # pragma: no cover - optional dependency
    from langgraph.graph import StateGraph

    LANGGRAPH_AVAILABLE = True
except ImportError:  # pragma: no cover - import guard
    LANGGRAPH_AVAILABLE = False


def _pipeline_context(state: WorkflowState) -> dict[str, Any]:
    data = state.case_data or {}
    return data.get("eb1a_pipeline", {})


async def node_generate_text(state: WorkflowState) -> WorkflowState:
    ctx = _pipeline_context(state)
    html_path = Path(ctx["html_path"])
    css_path = Path(ctx["css_path"]) if ctx.get("css_path") else None
    out_pdf = Path(ctx.get("text_pdf", "out/EB1A_text.pdf"))
    settings = get_settings()
    await generate_document(
        DocGenRequest(html_path=html_path, css_path=css_path, out_pdf=out_pdf), settings
    )
    state.agent_results.setdefault("eb1a", {})["text_pdf"] = str(out_pdf)
    state.workflow_step = "eb1a_generate_text"
    logger.info("eb1a.node_generate_text", out=str(out_pdf))
    return state


async def node_build_exhibits(state: WorkflowState) -> WorkflowState:
    ctx = _pipeline_context(state)
    exhibits_cfg = ctx.get("exhibits", [])
    processed = []
    for exhibit in exhibits_cfg:
        images = [Path(p) for p in exhibit.get("images", [])]
        out_pdf = Path(exhibit.get("out_pdf"))
        await analyze_images(images, out_pdf)
        if exhibit.get("finalize", True):
            finalized = out_pdf.with_name(out_pdf.stem + "_ocr.pdf")
            await finalize_pdf(out_pdf, finalized)
            processed.append(str(finalized))
        else:
            processed.append(str(out_pdf))
    state.agent_results.setdefault("eb1a", {})["exhibits"] = processed
    state.workflow_step = "eb1a_build_exhibits"
    logger.info("eb1a.node_build_exhibits", count=len(processed))
    return state


async def node_build_index(state: WorkflowState) -> WorkflowState:
    ctx = _pipeline_context(state)
    index_path = Path(ctx.get("index_path", "out/exhibits_index.json"))
    exhibit_paths = [Path(p) for p in state.agent_results.get("eb1a", {}).get("exhibits", [])]
    await build_index(exhibit_paths, index_path)
    state.agent_results.setdefault("eb1a", {})["index"] = str(index_path)
    state.workflow_step = "eb1a_build_index"
    logger.info("eb1a.node_build_index", out=str(index_path))
    return state


async def node_assemble_master(state: WorkflowState) -> WorkflowState:
    ctx = _pipeline_context(state)
    text_pdf = Path(state.agent_results.get("eb1a", {}).get("text_pdf"))
    index_path = Path(state.agent_results.get("eb1a", {}).get("index"))
    exhibits = [Path(p) for p in state.agent_results.get("eb1a", {}).get("exhibits", [])]
    out_pdf = Path(ctx.get("master_pdf", "out/EB1A_master.pdf"))
    await assemble_master_pdf(text_pdf, exhibits, index_path, out_pdf)
    state.agent_results.setdefault("eb1a", {})["master_pdf"] = str(out_pdf)
    state.workflow_step = "eb1a_assemble_master"
    logger.info("eb1a.node_assemble_master", out=str(out_pdf))
    return state


async def node_finalize_master(state: WorkflowState) -> WorkflowState:
    ctx = _pipeline_context(state)
    master_pdf = Path(state.agent_results.get("eb1a", {}).get("master_pdf"))
    out_pdf = Path(ctx.get("final_pdf", "out/EB1A_master_OCR.pdf"))
    provider = ctx.get("finalize_provider", "adobe")
    await finalize_master_pdf(master_pdf, out_pdf, provider=provider)
    state.agent_results.setdefault("eb1a", {})["final_pdf"] = str(out_pdf)
    state.workflow_step = "eb1a_finalize_master"
    logger.info("eb1a.node_finalize_master", out=str(out_pdf))
    return state


def build_eb1a_workflow() -> StateGraph:
    """Build a LangGraph workflow for EB-1A PDF generation."""

    if not LANGGRAPH_AVAILABLE:  # pragma: no cover - import guard
        raise RuntimeError("LangGraph is required to build the EB-1A workflow")

    graph = StateGraph(WorkflowState)
    graph.add_node("generate_text", node_generate_text)
    graph.add_node("build_exhibits", node_build_exhibits)
    graph.add_node("build_index", node_build_index)
    graph.add_node("assemble_master", node_assemble_master)
    graph.add_node("finalize_master", node_finalize_master)

    graph.set_entry_point("generate_text")
    graph.add_edge("generate_text", "build_exhibits")
    graph.add_edge("build_exhibits", "build_index")
    graph.add_edge("build_index", "assemble_master")
    graph.add_edge("assemble_master", "finalize_master")
    graph.set_finish_point("finalize_master")
    return graph
