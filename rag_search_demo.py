import asyncio
import tempfile
from pathlib import Path

from core.memory.memory_manager import MemoryManager
from core.groupagents.rag_pipeline_agent import RAGPipelineAgent, SearchQuery, SearchStrategy

async def main():
    """
    Демонстрация работы поиска в RAGPipelineAgent.
    """
    print("🚀 RAG Pipeline Agent Search Demo 🚀")
    print("=" * 40)

    # 1. Инициализация
    memory = MemoryManager()
    rag_agent = RAGPipelineAgent(memory_manager=memory)
    user_id = "demo-user-rag"

    # 2. Создание и обработка документа
    document_content = """
    LangGraph is a library for building stateful, multi-actor applications with LLMs.
    It extends the LangChain expression language with the ability to coordinate multiple chains (or actors) across multiple steps of computation in a cyclic manner.
    The main use case for LangGraph is for adding cycles to your LLM applications, which is a critical component of most agent runtimes.
    The core abstractions of LangGraph are:
    - Graph: a stateful graph that defines the structure of the application.
    - State: the representation of the application's state.
    - Nodes: the actors or functions that operate on the state.
    - Edges: the connections between nodes that determine the flow of the application.
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(document_content)
        temp_file_path = f.name

    print(f"\n📄 Processing document: {temp_file_path}")
    processed_doc = await rag_agent.aprocess_document(temp_file_path)
    print(f"✅ Document processed successfully. Chunks created: {len(processed_doc.chunks)}")

    # 3. Выполнение гибридного поиска
    query_text_hybrid = "what is langgraph used for?"
    print(f"\n🔍 Performing HYBRID search for: '{query_text_hybrid}'")

    search_query_hybrid = SearchQuery(
        query_text=query_text_hybrid,
        strategy=SearchStrategy.HYBRID,
        limit=3,
        similarity_threshold=0.01
    )
    search_response_hybrid = await rag_agent.asearch(search_query_hybrid, user_id=user_id)

    print("\n✨ Hybrid Search Response Object:")
    print(search_response_hybrid)

    print("\n✨ Hybrid Search Results:")
    if search_response_hybrid.results:
        for i, result in enumerate(search_response_hybrid.results, 1):
            print(f"  {i}. Score: {result.score:.4f}")
            print(f"     Content: {result.content[:150]}...")
    else:
        print("  No results found.")

    # 4. Очистка
    Path(temp_file_path).unlink()
    print(f"\n🗑️ Cleaned up temporary file: {temp_file_path}")

if __name__ == "__main__":
    asyncio.run(main())
