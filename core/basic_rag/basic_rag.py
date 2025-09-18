"""
Basic RAG System для mega_agent_pro.

Базовая система RAG (Retrieval-Augmented Generation) включающая:
- Обработку и индексацию документов
- Векторное хранение и поиск
- Семантический поиск по документам
- Интеграцию с LLM для генерации ответов
- Стратегии разбивки документов на chunks
- Обработку пользовательских запросов
- Простую RAG pipeline
"""

from __future__ import annotations

import hashlib
import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChunkingStrategy(str, Enum):
    """Стратегии разбивки документов"""
    FIXED_SIZE = "fixed_size"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    SEMANTIC = "semantic"


class SearchType(str, Enum):
    """Типы поиска"""
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


class Document(BaseModel):
    """Документ для обработки"""
    id: str = Field(..., description="Уникальный ID документа")
    title: str = Field(..., description="Название документа")
    content: str = Field(..., description="Содержимое документа")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Метаданные")
    source: Optional[str] = Field(default=None, description="Источник документа")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentChunk(BaseModel):
    """Часть документа (chunk)"""
    id: str = Field(..., description="ID части")
    document_id: str = Field(..., description="ID исходного документа")
    content: str = Field(..., description="Содержимое части")
    embedding: List[float] = Field(default_factory=list, description="Вектор эмбеддинга")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Метаданные части")
    chunk_index: int = Field(..., description="Номер части в документе")
    start_char: int = Field(default=0, description="Начальная позиция в тексте")
    end_char: int = Field(default=0, description="Конечная позиция в тексте")


class SearchResult(BaseModel):
    """Результат поиска"""
    chunk: DocumentChunk = Field(..., description="Найденная часть документа")
    score: float = Field(..., description="Релевантность (0-1)")
    rank: int = Field(..., description="Ранг в результатах")
    distance: float = Field(default=0.0, description="Расстояние в векторном пространстве")


class RAGQuery(BaseModel):
    """Запрос к RAG системе"""
    query: str = Field(..., description="Пользовательский запрос")
    max_results: int = Field(default=5, description="Максимум результатов поиска")
    search_type: SearchType = Field(default=SearchType.SEMANTIC, description="Тип поиска")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Фильтры поиска")
    user_id: Optional[str] = Field(default=None, description="ID пользователя")
    context: Dict[str, Any] = Field(default_factory=dict, description="Контекст запроса")


class RAGResponse(BaseModel):
    """Ответ RAG системы"""
    query: str = Field(..., description="Исходный запрос")
    answer: str = Field(..., description="Сгенерированный ответ")
    sources: List[SearchResult] = Field(..., description="Источники информации")
    confidence: float = Field(..., description="Уверенность в ответе")
    latency: float = Field(..., description="Время обработки")
    tokens_used: int = Field(default=0, description="Использовано токенов")
    success: bool = Field(default=True, description="Успешность обработки")
    error: Optional[str] = Field(default=None, description="Ошибка если есть")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Дополнительные данные")


class DocumentProcessor:
    """Обработчик документов"""

    def __init__(self, chunking_strategy: ChunkingStrategy = ChunkingStrategy.FIXED_SIZE):
        self.chunking_strategy = chunking_strategy
        self.chunk_size = 500  # Размер части по умолчанию
        self.chunk_overlap = 50  # Перекрытие между частями

    async def process_document(self, document: Document) -> List[DocumentChunk]:
        """Обработка документа и разбивка на части"""
        chunks = []

        if self.chunking_strategy == ChunkingStrategy.FIXED_SIZE:
            chunks = await self._chunk_by_fixed_size(document)
        elif self.chunking_strategy == ChunkingStrategy.SENTENCE:
            chunks = await self._chunk_by_sentences(document)
        elif self.chunking_strategy == ChunkingStrategy.PARAGRAPH:
            chunks = await self._chunk_by_paragraphs(document)
        elif self.chunking_strategy == ChunkingStrategy.SEMANTIC:
            chunks = await self._chunk_semantically(document)

        return chunks

    async def _chunk_by_fixed_size(self, document: Document) -> List[DocumentChunk]:
        """Разбивка по фиксированному размеру"""
        chunks = []
        content = document.content

        for i in range(0, len(content), self.chunk_size - self.chunk_overlap):
            chunk_content = content[i:i + self.chunk_size]

            if not chunk_content.strip():
                continue

            chunk_id = f"{document.id}_chunk_{len(chunks)}"

            chunk = DocumentChunk(
                id=chunk_id,
                document_id=document.id,
                content=chunk_content,
                chunk_index=len(chunks),
                start_char=i,
                end_char=min(i + self.chunk_size, len(content)),
                metadata={
                    "document_title": document.title,
                    "document_source": document.source,
                    "chunking_strategy": self.chunking_strategy.value
                }
            )

            chunks.append(chunk)

        return chunks

    async def _chunk_by_sentences(self, document: Document) -> List[DocumentChunk]:
        """Разбивка по предложениям"""
        # Простая разбивка по точкам (в реальности нужен более сложный парсер)
        sentences = [s.strip() for s in document.content.split('.') if s.strip()]

        chunks = []
        current_chunk = ""
        current_start = 0

        for sentence in sentences:
            if len(current_chunk) + len(sentence) > self.chunk_size and current_chunk:
                # Создаем chunk
                chunk_id = f"{document.id}_sent_chunk_{len(chunks)}"

                chunk = DocumentChunk(
                    id=chunk_id,
                    document_id=document.id,
                    content=current_chunk,
                    chunk_index=len(chunks),
                    start_char=current_start,
                    end_char=current_start + len(current_chunk),
                    metadata={
                        "document_title": document.title,
                        "chunking_strategy": self.chunking_strategy.value
                    }
                )

                chunks.append(chunk)
                current_chunk = sentence
                current_start += len(current_chunk) + 1
            else:
                if current_chunk:
                    current_chunk += ". " + sentence
                else:
                    current_chunk = sentence

        # Последний chunk
        if current_chunk:
            chunk_id = f"{document.id}_sent_chunk_{len(chunks)}"

            chunk = DocumentChunk(
                id=chunk_id,
                document_id=document.id,
                content=current_chunk,
                chunk_index=len(chunks),
                start_char=current_start,
                end_char=current_start + len(current_chunk),
                metadata={
                    "document_title": document.title,
                    "chunking_strategy": self.chunking_strategy.value
                }
            )

            chunks.append(chunk)

        return chunks

    async def _chunk_by_paragraphs(self, document: Document) -> List[DocumentChunk]:
        """Разбивка по абзацам"""
        paragraphs = [p.strip() for p in document.content.split('\n\n') if p.strip()]

        chunks = []
        for i, paragraph in enumerate(paragraphs):
            chunk_id = f"{document.id}_para_chunk_{i}"

            chunk = DocumentChunk(
                id=chunk_id,
                document_id=document.id,
                content=paragraph,
                chunk_index=i,
                start_char=0,  # Упрощение для демо
                end_char=len(paragraph),
                metadata={
                    "document_title": document.title,
                    "chunking_strategy": self.chunking_strategy.value
                }
            )

            chunks.append(chunk)

        return chunks

    async def _chunk_semantically(self, document: Document) -> List[DocumentChunk]:
        """Семантическая разбивка (упрощенная)"""
        # В реальности здесь был бы сложный анализ семантики
        # Пока используем комбинацию предложений и размера
        return await self._chunk_by_sentences(document)


class VectorStore:
    """Простое векторное хранилище"""

    def __init__(self):
        self.chunks: Dict[str, DocumentChunk] = {}
        self.embeddings: Dict[str, List[float]] = {}

    async def add_chunk(self, chunk: DocumentChunk) -> bool:
        """Добавить chunk в хранилище"""
        try:
            self.chunks[chunk.id] = chunk
            if chunk.embedding:
                self.embeddings[chunk.id] = chunk.embedding
            return True
        except Exception:
            return False

    async def add_chunks(self, chunks: List[DocumentChunk]) -> int:
        """Добавить несколько chunks"""
        added = 0
        for chunk in chunks:
            if await self.add_chunk(chunk):
                added += 1
        return added

    async def search_similar(self, query_embedding: List[float], max_results: int = 5) -> List[SearchResult]:
        """Поиск похожих chunks"""
        if not query_embedding or not self.embeddings:
            return []

        # Вычисляем косинусное сходство
        similarities = []

        for chunk_id, embedding in self.embeddings.items():
            similarity = self._cosine_similarity(query_embedding, embedding)
            similarities.append((chunk_id, similarity))

        # Сортируем по сходству
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Формируем результаты
        results = []
        for i, (chunk_id, similarity) in enumerate(similarities[:max_results]):
            chunk = self.chunks[chunk_id]

            result = SearchResult(
                chunk=chunk,
                score=similarity,
                rank=i + 1,
                distance=1.0 - similarity
            )

            results.append(result)

        return results

    async def search_keyword(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Поиск по ключевым словам"""
        query_lower = query.lower()
        matches = []

        for chunk_id, chunk in self.chunks.items():
            content_lower = chunk.content.lower()

            # Простое совпадение по ключевым словам
            score = 0.0
            words = query_lower.split()

            for word in words:
                if word in content_lower:
                    score += content_lower.count(word) / len(content_lower)

            if score > 0:
                matches.append((chunk_id, score))

        # Сортируем по релевантности
        matches.sort(key=lambda x: x[1], reverse=True)

        results = []
        for i, (chunk_id, score) in enumerate(matches[:max_results]):
            chunk = self.chunks[chunk_id]

            result = SearchResult(
                chunk=chunk,
                score=min(score, 1.0),  # Ограничиваем до 1.0
                rank=i + 1,
                distance=0.0
            )

            results.append(result)

        return results

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Вычисление косинусного сходства"""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    async def get_chunk(self, chunk_id: str) -> Optional[DocumentChunk]:
        """Получить chunk по ID"""
        return self.chunks.get(chunk_id)

    async def delete_document(self, document_id: str) -> int:
        """Удалить все chunks документа"""
        to_delete = [chunk_id for chunk_id, chunk in self.chunks.items()
                    if chunk.document_id == document_id]

        for chunk_id in to_delete:
            del self.chunks[chunk_id]
            if chunk_id in self.embeddings:
                del self.embeddings[chunk_id]

        return len(to_delete)

    def get_stats(self) -> Dict[str, Any]:
        """Статистика хранилища"""
        return {
            "total_chunks": len(self.chunks),
            "total_embeddings": len(self.embeddings),
            "documents": len(set(chunk.document_id for chunk in self.chunks.values()))
        }


class QueryProcessor:
    """Обработчик запросов"""

    def __init__(self, embedder=None, llm_router=None):
        self.embedder = embedder
        self.llm_router = llm_router

    async def process_query(self, query: RAGQuery) -> List[float]:
        """Обработка запроса и получение эмбеддинга"""
        if not self.embedder:
            # Если нет embedder, возвращаем mock эмбеддинг
            return self._generate_mock_embedding(query.query)

        # Используем simple embedder
        try:
            from core.simple_embedder import EmbedRequest

            embed_request = EmbedRequest(texts=[query.query])
            response = await self.embedder.embed(embed_request)

            if response.success and response.embeddings:
                return response.embeddings[0]
            else:
                return self._generate_mock_embedding(query.query)

        except Exception:
            return self._generate_mock_embedding(query.query)

    async def generate_answer(self, query: str, context: List[SearchResult]) -> str:
        """Генерация ответа на основе найденного контекста"""
        if not self.llm_router or not context:
            return self._generate_simple_answer(query, context)

        try:
            # Подготовка контекста
            context_text = "\n\n".join([
                f"Источник {i+1}: {result.chunk.content}"
                for i, result in enumerate(context[:3])  # Берем топ-3
            ])

            # Формируем prompt
            messages = [
                {
                    "role": "system",
                    "content": "Ты полезный ассистент. Отвечай на вопросы на основе предоставленного контекста."
                },
                {
                    "role": "user",
                    "content": f"Контекст:\n{context_text}\n\nВопрос: {query}\n\nОтвет:"
                }
            ]

            # Используем LLM router
            from core.llm_router import LLMRequest, ModelType

            llm_request = LLMRequest(
                messages=messages,
                model_type=ModelType.CHAT,
                max_tokens=500,
                temperature=0.7
            )

            response = await self.llm_router.route_request(llm_request)

            if response.success:
                return response.content
            else:
                return self._generate_simple_answer(query, context)

        except Exception:
            return self._generate_simple_answer(query, context)

    def _generate_mock_embedding(self, text: str) -> List[float]:
        """Генерация mock эмбеддинга"""
        # Детерминированный mock вектор на основе хеша
        text_hash = hashlib.md5(text.encode()).hexdigest()
        import random
        random.seed(int(text_hash[:8], 16))

        return [random.gauss(0, 0.1) for _ in range(384)]

    def _generate_simple_answer(self, query: str, context: List[SearchResult]) -> str:
        """Простая генерация ответа без LLM"""
        if not context:
            return f"Извините, я не нашел информации по запросу: '{query}'"

        # Берем самый релевантный результат
        best_match = context[0]

        return (f"На основе найденной информации: {best_match.chunk.content[:200]}... "
                f"(релевантность: {best_match.score:.2f})")


class RAGPipeline:
    """Основная RAG pipeline"""

    def __init__(self, embedder=None, llm_router=None):
        self.document_processor = DocumentProcessor()
        self.vector_store = VectorStore()
        self.query_processor = QueryProcessor(embedder, llm_router)

    async def index_document(self, document: Document) -> bool:
        """Индексация документа"""
        try:
            # 1. Разбиваем документ на chunks
            chunks = await self.document_processor.process_document(document)

            # 2. Создаем эмбеддинги для chunks
            if self.query_processor.embedder:
                for chunk in chunks:
                    try:
                        from core.simple_embedder import EmbedRequest

                        embed_request = EmbedRequest(texts=[chunk.content])
                        response = await self.query_processor.embedder.embed(embed_request)

                        if response.success and response.embeddings:
                            chunk.embedding = response.embeddings[0]
                        else:
                            # Fallback на mock эмбеддинг
                            chunk.embedding = self.query_processor._generate_mock_embedding(chunk.content)
                    except Exception:
                        chunk.embedding = self.query_processor._generate_mock_embedding(chunk.content)
            else:
                # Mock эмбеддинги
                for chunk in chunks:
                    chunk.embedding = self.query_processor._generate_mock_embedding(chunk.content)

            # 3. Добавляем в vector store
            added = await self.vector_store.add_chunks(chunks)

            return added > 0

        except Exception:
            return False

    async def search(self, query: RAGQuery) -> List[SearchResult]:
        """Поиск релевантной информации"""
        results = []

        try:
            if query.search_type == SearchType.SEMANTIC:
                # Семантический поиск
                query_embedding = await self.query_processor.process_query(query)
                results = await self.vector_store.search_similar(query_embedding, query.max_results)

            elif query.search_type == SearchType.KEYWORD:
                # Поиск по ключевым словам
                results = await self.vector_store.search_keyword(query.query, query.max_results)

            elif query.search_type == SearchType.HYBRID:
                # Гибридный поиск (комбинирует семантический и keyword)
                query_embedding = await self.query_processor.process_query(query)
                semantic_results = await self.vector_store.search_similar(query_embedding, query.max_results)
                keyword_results = await self.vector_store.search_keyword(query.query, query.max_results)

                # Простое объединение результатов
                combined = {}
                for result in semantic_results:
                    combined[result.chunk.id] = result

                for result in keyword_results:
                    if result.chunk.id in combined:
                        # Усредняем scores
                        combined[result.chunk.id].score = (combined[result.chunk.id].score + result.score) / 2
                    else:
                        combined[result.chunk.id] = result

                results = list(combined.values())
                results.sort(key=lambda x: x.score, reverse=True)
                results = results[:query.max_results]

        except Exception:
            pass

        return results

    async def query(self, query: RAGQuery) -> RAGResponse:
        """Полный RAG запрос с генерацией ответа"""
        start_time = time.time()

        try:
            # 1. Поиск релевантной информации
            search_results = await self.search(query)

            # 2. Генерация ответа
            answer = await self.query_processor.generate_answer(query.query, search_results)

            # 3. Оценка уверенности
            confidence = self._calculate_confidence(search_results)

            latency = time.time() - start_time

            return RAGResponse(
                query=query.query,
                answer=answer,
                sources=search_results,
                confidence=confidence,
                latency=latency,
                success=True,
                metadata={
                    "search_type": query.search_type.value,
                    "results_count": len(search_results)
                }
            )

        except Exception as e:
            latency = time.time() - start_time

            return RAGResponse(
                query=query.query,
                answer="Извините, произошла ошибка при обработке запроса.",
                sources=[],
                confidence=0.0,
                latency=latency,
                success=False,
                error=str(e)
            )

    def _calculate_confidence(self, results: List[SearchResult]) -> float:
        """Расчет уверенности в ответе"""
        if not results:
            return 0.0

        # Простая формула на основе топового результата и количества результатов
        top_score = results[0].score
        result_count_factor = min(len(results) / 5.0, 1.0)  # Больше результатов = выше уверенность

        confidence = top_score * 0.7 + result_count_factor * 0.3
        return min(confidence, 1.0)

    async def get_document_info(self, document_id: str) -> Dict[str, Any]:
        """Информация о документе"""
        chunks = [chunk for chunk in self.vector_store.chunks.values()
                 if chunk.document_id == document_id]

        if not chunks:
            return {}

        return {
            "document_id": document_id,
            "chunks_count": len(chunks),
            "total_content_length": sum(len(chunk.content) for chunk in chunks),
            "first_chunk": chunks[0].metadata.get("document_title", "Unknown")
        }

    async def delete_document(self, document_id: str) -> bool:
        """Удаление документа"""
        try:
            deleted = await self.vector_store.delete_document(document_id)
            return deleted > 0
        except Exception:
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Статистика RAG системы"""
        store_stats = self.vector_store.get_stats()

        return {
            "vector_store": store_stats,
            "chunking_strategy": self.document_processor.chunking_strategy.value,
            "chunk_size": self.document_processor.chunk_size,
            "has_embedder": self.query_processor.embedder is not None,
            "has_llm": self.query_processor.llm_router is not None
        }


class BasicRAG:
    """Основной класс для RAG системы"""

    def __init__(self, embedder=None, llm_router=None):
        self.pipeline = RAGPipeline(embedder, llm_router)

    async def add_document(self, title: str, content: str, metadata: Dict[str, Any] = None) -> str:
        """Добавление документа"""
        document_id = hashlib.md5(f"{title}{content}".encode()).hexdigest()

        document = Document(
            id=document_id,
            title=title,
            content=content,
            metadata=metadata or {}
        )

        success = await self.pipeline.index_document(document)
        return document_id if success else None

    async def search(self, query: str, max_results: int = 5, search_type: str = "semantic") -> RAGResponse:
        """Поиск и генерация ответа"""
        rag_query = RAGQuery(
            query=query,
            max_results=max_results,
            search_type=SearchType(search_type)
        )

        return await self.pipeline.query(rag_query)

    async def get_stats(self) -> Dict[str, Any]:
        """Статистика системы"""
        return self.pipeline.get_stats()


async def create_basic_rag(embedder=None, llm_router=None) -> BasicRAG:
    """Фабрика для создания Basic RAG"""
    return BasicRAG(embedder, llm_router)