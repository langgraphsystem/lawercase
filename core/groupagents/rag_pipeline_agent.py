"""
RAGPipelineAgent - Гибридный поиск и RAG (Retrieval Augmented Generation).

Обеспечивает:
- Hybrid retrieval (dense + sparse + graph)
- Gemini embeddings integration
- Contextual chunking
- Cross-encoder reranking
- Semantic caching
- File parsing (PDF, DOCX, HTML, MD, Images)
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..memory.memory_manager import MemoryManager
from ..memory.models import AuditEvent


class DocumentType(str, Enum):
    """Типы документов для обработки"""
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"
    MARKDOWN = "markdown"
    TXT = "txt"
    IMAGE = "image"
    JSON = "json"
    XML = "xml"


class SearchStrategy(str, Enum):
    """Стратегии поиска"""
    DENSE_ONLY = "dense_only"
    SPARSE_ONLY = "sparse_only"
    HYBRID = "hybrid"
    GRAPH_ENHANCED = "graph_enhanced"
    SEMANTIC_SIMILARITY = "semantic_similarity"


class ChunkingStrategy(str, Enum):
    """Стратегии разбиения на чанки"""
    FIXED_SIZE = "fixed_size"
    SENTENCE_BASED = "sentence_based"
    PARAGRAPH_BASED = "paragraph_based"
    SEMANTIC_BASED = "semantic_based"
    CONTEXTUAL = "contextual"


class DocumentChunk(BaseModel):
    """Чанк документа"""
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = Field(..., description="ID исходного документа")
    content: str = Field(..., description="Содержимое чанка")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Метаданные чанка")
    embedding: Optional[List[float]] = Field(None, description="Векторное представление")
    position: int = Field(..., description="Позиция в документе")
    chunk_type: str = Field(default="text", description="Тип чанка")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProcessedDocument(BaseModel):
    """Обработанный документ"""
    document_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = Field(..., description="Название документа")
    file_path: str = Field(..., description="Путь к файлу")
    document_type: DocumentType = Field(..., description="Тип документа")
    content: str = Field(..., description="Извлеченное содержимое")
    chunks: List[DocumentChunk] = Field(default_factory=list, description="Чанки документа")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Метаданные документа")
    processing_stats: Dict[str, Any] = Field(default_factory=dict, description="Статистика обработки")
    processed_at: datetime = Field(default_factory=datetime.utcnow)
    file_hash: Optional[str] = Field(None, description="Хэш файла")


class SearchQuery(BaseModel):
    """Поисковый запрос"""
    query_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query_text: str = Field(..., description="Текст запроса")
    strategy: SearchStrategy = Field(default=SearchStrategy.HYBRID, description="Стратегия поиска")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Фильтры поиска")
    limit: int = Field(default=10, ge=1, le=100, description="Лимит результатов")
    rerank: bool = Field(default=True, description="Использовать reranking")
    include_metadata: bool = Field(default=True, description="Включать метаданные")
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Порог схожести")


class SearchResult(BaseModel):
    """Результат поиска"""
    result_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    chunk_id: str = Field(..., description="ID чанка")
    document_id: str = Field(..., description="ID документа")
    content: str = Field(..., description="Содержимое результата")
    score: float = Field(..., description="Оценка релевантности")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Метаданные")
    highlights: List[str] = Field(default_factory=list, description="Выделенные фрагменты")


class SearchResponse(BaseModel):
    """Ответ поиска"""
    query_id: str = Field(..., description="ID запроса")
    results: List[SearchResult] = Field(default_factory=list, description="Результаты поиска")
    total_found: int = Field(..., description="Общее количество найденных")
    search_time: float = Field(..., description="Время поиска в секундах")
    strategy_used: SearchStrategy = Field(..., description="Использованная стратегия")
    cache_hit: bool = Field(default=False, description="Результат из кэша")
    aggregated_content: Optional[str] = Field(None, description="Агрегированное содержимое")


class EmbeddingRequest(BaseModel):
    """Запрос на эмбеддинги"""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    texts: List[str] = Field(..., description="Тексты для эмбеддинга")
    model: str = Field(default="gemini", description="Модель эмбеддинга")
    batch_size: int = Field(default=100, description="Размер батча")


class CacheEntry(BaseModel):
    """Запись в кэше"""
    cache_key: str = Field(..., description="Ключ кэша")
    content: Any = Field(..., description="Содержимое кэша")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    access_count: int = Field(default=0, description="Количество обращений")
    last_accessed: datetime = Field(default_factory=datetime.utcnow)


class RAGError(Exception):
    """Исключение для ошибок RAG"""
    pass


class EmbeddingError(Exception):
    """Исключение для ошибок эмбеддинга"""
    pass


class RAGPipelineAgent:
    """
    Агент для гибридного поиска и RAG functionality.

    Основные функции:
    - Hybrid retrieval с комбинацией dense, sparse и graph поиска
    - Gemini embeddings integration
    - Contextual chunking с различными стратегиями
    - Cross-encoder reranking для улучшения релевантности
    - Multi-level semantic caching
    - File parsing для различных форматов
    """

    def __init__(self, memory_manager: Optional[MemoryManager] = None):
        """
        Инициализация RAGPipelineAgent.

        Args:
            memory_manager: Менеджер памяти для persistence
        """
        self.memory = memory_manager or MemoryManager()

        # Хранилища
        self._documents: Dict[str, ProcessedDocument] = {}
        self._chunks: Dict[str, DocumentChunk] = {}
        self._embeddings_cache: Dict[str, List[float]] = {}
        self._search_cache: Dict[str, CacheEntry] = {}

        # Конфигурация
        self._embedding_dimension = 1536  # Размерность эмбеддинга
        self._chunk_size = 512  # Размер чанка по умолчанию
        self._chunk_overlap = 50  # Перекрытие чанков

        # Статистика
        self._processing_stats: Dict[str, int] = {}
        self._search_stats: Dict[str, int] = {}

    async def aprocess_document(
        self,
        file_path: str,
        chunking_strategy: ChunkingStrategy = ChunkingStrategy.CONTEXTUAL,
        user_id: str = "system"
    ) -> ProcessedDocument:
        """
        Обработка документа с извлечением содержимого и chunking.

        Args:
            file_path: Путь к файлу
            chunking_strategy: Стратегия разбиения на чанки
            user_id: ID пользователя

        Returns:
            ProcessedDocument: Обработанный документ

        Raises:
            RAGError: При ошибках обработки
        """
        start_time = datetime.utcnow()

        try:
            # Определение типа документа
            document_type = await self._detect_document_type(file_path)

            # Извлечение содержимого
            content = await self._extract_content(file_path, document_type)

            # Вычисление хэша файла
            file_hash = await self._calculate_file_hash(file_path)

            # Проверка кэша по хэшу
            cached_doc = await self._get_cached_document(file_hash)
            if cached_doc:
                await self._log_document_processing(cached_doc, user_id, cache_hit=True)
                return cached_doc

            # Создание документа
            document = ProcessedDocument(
                title=Path(file_path).stem,
                file_path=file_path,
                document_type=document_type,
                content=content,
                file_hash=file_hash
            )

            # Chunking содержимого
            chunks = await self._chunk_content(content, chunking_strategy, document.document_id)
            document.chunks = chunks

            # Генерация эмбеддингов для чанков
            await self._generate_embeddings_for_chunks(chunks)

            # Статистика обработки
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            document.processing_stats = {
                "processing_time": processing_time,
                "chunks_count": len(chunks),
                "content_length": len(content),
                "chunking_strategy": chunking_strategy.value
            }

            # Сохранение документа
            self._documents[document.document_id] = document

            # Сохранение чанков
            for chunk in chunks:
                self._chunks[chunk.chunk_id] = chunk

            # Audit log
            await self._log_document_processing(document, user_id)

            # Обновление статистики
            self._update_processing_stats(document_type)

            return document

        except Exception as e:
            await self._log_processing_error(file_path, user_id, e)
            raise RAGError(f"Failed to process document: {str(e)}")

    async def asearch(
        self,
        query: SearchQuery,
        user_id: str = "system"
    ) -> SearchResponse:
        """
        Гибридный поиск по обработанным документам.

        Args:
            query: Поисковый запрос
            user_id: ID пользователя

        Returns:
            SearchResponse: Результаты поиска

        Raises:
            RAGError: При ошибках поиска
        """
        start_time = datetime.utcnow()

        try:
            # Проверка кэша поиска
            cache_key = self._generate_search_cache_key(query)
            cached_response = await self._get_cached_search(cache_key)
            if cached_response:
                await self._log_search(query, cached_response, user_id, cache_hit=True)
                return cached_response

            # Генерация эмбеддинга для запроса
            query_embedding = await self._generate_query_embedding(query.query_text)

            # Выполнение поиска по выбранной стратегии
            if query.strategy == SearchStrategy.DENSE_ONLY:
                results = await self._dense_search(query_embedding, query)
            elif query.strategy == SearchStrategy.SPARSE_ONLY:
                results = await self._sparse_search(query.query_text, query)
            elif query.strategy == SearchStrategy.HYBRID:
                results = await self._hybrid_search(query_embedding, query.query_text, query)
            elif query.strategy == SearchStrategy.GRAPH_ENHANCED:
                results = await self._graph_enhanced_search(query_embedding, query.query_text, query)
            else:
                results = await self._semantic_similarity_search(query_embedding, query)

            # Reranking результатов
            if query.rerank and len(results) > 1:
                results = await self._rerank_results(query.query_text, results)

            # Применение лимита
            results = results[:query.limit]

            # Генерация highlights
            for result in results:
                result.highlights = await self._generate_highlights(query.query_text, result.content)

            # Агрегация содержимого
            aggregated_content = await self._aggregate_content(results) if results else None

            # Расчет времени поиска
            search_time = (datetime.utcnow() - start_time).total_seconds()

            # Создание ответа
            response = SearchResponse(
                query_id=query.query_id,
                results=results,
                total_found=len(results),
                search_time=search_time,
                strategy_used=query.strategy,
                aggregated_content=aggregated_content
            )

            # Кэширование результата
            await self._cache_search_result(cache_key, response)

            # Audit log
            await self._log_search(query, response, user_id)

            # Обновление статистики
            self._update_search_stats(query.strategy)

            return response

        except Exception as e:
            await self._log_search_error(query, user_id, e)
            raise RAGError(f"Search failed: {str(e)}")

    async def aembed_gemini(
        self,
        request: EmbeddingRequest,
        user_id: str = "system"
    ) -> Dict[str, List[float]]:
        """
        Генерация эмбеддингов через Gemini API.

        Args:
            request: Запрос на эмбеддинги
            user_id: ID пользователя

        Returns:
            Dict[str, List[float]]: Словарь текст -> эмбеддинг

        Raises:
            EmbeddingError: При ошибках генерации эмбеддингов
        """
        try:
            embeddings = {}

            # Обработка батчами
            for i in range(0, len(request.texts), request.batch_size):
                batch = request.texts[i:i + request.batch_size]

                # Проверка кэша для каждого текста
                batch_embeddings = {}
                texts_to_embed = []

                for text in batch:
                    text_hash = hashlib.md5(text.encode()).hexdigest()
                    cached_embedding = self._embeddings_cache.get(text_hash)

                    if cached_embedding:
                        batch_embeddings[text] = cached_embedding
                    else:
                        texts_to_embed.append(text)

                # Генерация эмбеддингов для новых текстов
                if texts_to_embed:
                    new_embeddings = await self._generate_embeddings_batch(texts_to_embed, request.model)

                    # Кэширование новых эмбеддингов
                    for text, embedding in new_embeddings.items():
                        text_hash = hashlib.md5(text.encode()).hexdigest()
                        self._embeddings_cache[text_hash] = embedding
                        batch_embeddings[text] = embedding

                embeddings.update(batch_embeddings)

            # Audit log
            await self._log_embedding_generation(request, len(embeddings), user_id)

            return embeddings

        except Exception as e:
            await self._log_embedding_error(request, user_id, e)
            raise EmbeddingError(f"Embedding generation failed: {str(e)}")

    async def achunk(
        self,
        content: str,
        strategy: ChunkingStrategy = ChunkingStrategy.CONTEXTUAL,
        document_id: Optional[str] = None
    ) -> List[DocumentChunk]:
        """
        Contextual chunking содержимого.

        Args:
            content: Содержимое для разбиения
            strategy: Стратегия chunking
            document_id: ID документа

        Returns:
            List[DocumentChunk]: Список чанков
        """
        try:
            return await self._chunk_content(content, strategy, document_id or str(uuid.uuid4()))

        except Exception as e:
            raise RAGError(f"Chunking failed: {str(e)}")

    async def _detect_document_type(self, file_path: str) -> DocumentType:
        """Определение типа документа по расширению"""
        extension = Path(file_path).suffix.lower()

        type_mapping = {
            ".pdf": DocumentType.PDF,
            ".docx": DocumentType.DOCX,
            ".html": DocumentType.HTML,
            ".htm": DocumentType.HTML,
            ".md": DocumentType.MARKDOWN,
            ".txt": DocumentType.TXT,
            ".json": DocumentType.JSON,
            ".xml": DocumentType.XML,
            ".jpg": DocumentType.IMAGE,
            ".jpeg": DocumentType.IMAGE,
            ".png": DocumentType.IMAGE,
            ".gif": DocumentType.IMAGE
        }

        return type_mapping.get(extension, DocumentType.TXT)

    async def _extract_content(self, file_path: str, document_type: DocumentType) -> str:
        """Извлечение содержимого из файла"""
        try:
            if document_type == DocumentType.TXT:
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()

            elif document_type == DocumentType.MARKDOWN:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Простая обработка Markdown (в реальности использовать markdown parser)
                    return content.replace("#", "").replace("*", "").replace("_", "")

            elif document_type == DocumentType.JSON:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return json.dumps(data, indent=2, ensure_ascii=False)

            elif document_type == DocumentType.HTML:
                # Заглушка для HTML парсинга (в реальности использовать BeautifulSoup)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Простое удаление HTML тегов
                    import re
                    clean_content = re.sub(r'<[^>]+>', '', content)
                    return clean_content

            elif document_type == DocumentType.PDF:
                # Заглушка для PDF парсинга (в реальности использовать PyPDF2 или pdfplumber)
                return f"PDF content from {file_path} - extracted text would be here"

            elif document_type == DocumentType.DOCX:
                # Заглушка для DOCX парсинга (в реальности использовать python-docx)
                return f"DOCX content from {file_path} - extracted text would be here"

            elif document_type == DocumentType.IMAGE:
                # Заглушка для OCR (в реальности использовать Tesseract или Cloud Vision API)
                return f"OCR text from image {file_path} - extracted text would be here"

            else:
                return f"Unsupported document type: {document_type}"

        except Exception as e:
            raise RAGError(f"Content extraction failed: {str(e)}")

    async def _chunk_content(
        self,
        content: str,
        strategy: ChunkingStrategy,
        document_id: str
    ) -> List[DocumentChunk]:
        """Разбиение содержимого на чанки"""
        chunks = []

        if strategy == ChunkingStrategy.FIXED_SIZE:
            # Разбиение на фиксированные размеры
            for i in range(0, len(content), self._chunk_size):
                chunk_content = content[i:i + self._chunk_size]
                if chunk_content.strip():
                    chunk = DocumentChunk(
                        document_id=document_id,
                        content=chunk_content,
                        position=i // self._chunk_size,
                        metadata={"strategy": strategy.value}
                    )
                    chunks.append(chunk)

        elif strategy == ChunkingStrategy.SENTENCE_BASED:
            # Разбиение по предложениям
            sentences = content.split(". ")
            current_chunk = ""
            position = 0

            for sentence in sentences:
                if len(current_chunk + sentence) > self._chunk_size and current_chunk:
                    chunk = DocumentChunk(
                        document_id=document_id,
                        content=current_chunk.strip(),
                        position=position,
                        metadata={"strategy": strategy.value}
                    )
                    chunks.append(chunk)
                    current_chunk = sentence
                    position += 1
                else:
                    current_chunk += sentence + ". "

            # Последний чанк
            if current_chunk.strip():
                chunk = DocumentChunk(
                    document_id=document_id,
                    content=current_chunk.strip(),
                    position=position,
                    metadata={"strategy": strategy.value}
                )
                chunks.append(chunk)

        elif strategy == ChunkingStrategy.PARAGRAPH_BASED:
            # Разбиение по параграфам
            paragraphs = content.split("\n\n")
            for i, paragraph in enumerate(paragraphs):
                if paragraph.strip():
                    chunk = DocumentChunk(
                        document_id=document_id,
                        content=paragraph.strip(),
                        position=i,
                        metadata={"strategy": strategy.value}
                    )
                    chunks.append(chunk)

        elif strategy == ChunkingStrategy.CONTEXTUAL:
            # Контекстуальное разбиение (упрощенная версия)
            # В реальности использовать более сложные алгоритмы
            return await self._chunk_content(content, ChunkingStrategy.SENTENCE_BASED, document_id)

        else:
            # Fallback к фиксированному размеру
            return await self._chunk_content(content, ChunkingStrategy.FIXED_SIZE, document_id)

        return chunks

    async def _generate_embeddings_for_chunks(self, chunks: List[DocumentChunk]) -> None:
        """Генерация эмбеддингов для чанков"""
        texts = [chunk.content for chunk in chunks]

        # Создание запроса на эмбеддинги
        embedding_request = EmbeddingRequest(texts=texts)

        # Генерация эмбеддингов
        embeddings = await self.aembed_gemini(embedding_request)

        # Присвоение эмбеддингов чанкам
        for chunk in chunks:
            chunk.embedding = embeddings.get(chunk.content, [])

    async def _generate_query_embedding(self, query_text: str) -> List[float]:
        """Генерация эмбеддинга для запроса"""
        embedding_request = EmbeddingRequest(texts=[query_text])
        embeddings = await self.aembed_gemini(embedding_request)
        return embeddings.get(query_text, [])

    async def _generate_embeddings_batch(
        self,
        texts: List[str],
        model: str
    ) -> Dict[str, List[float]]:
        """Генерация батча эмбеддингов"""
        # Заглушка для Gemini API
        # В реальности здесь будет вызов к Gemini Embeddings API
        embeddings = {}

        for text in texts:
            # Генерация случайного эмбеддинга для демонстрации
            import random
            random.seed(hash(text) % (2**32))
            embedding = [random.uniform(-1, 1) for _ in range(self._embedding_dimension)]
            embeddings[text] = embedding

        return embeddings

    async def _dense_search(
        self,
        query_embedding: List[float],
        query: SearchQuery
    ) -> List[SearchResult]:
        """Dense (векторный) поиск"""
        results = []

        for chunk in self._chunks.values():
            if not chunk.embedding:
                continue

            # Вычисление cosine similarity
            similarity = self._cosine_similarity(query_embedding, chunk.embedding)

            if similarity >= query.similarity_threshold:
                result = SearchResult(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    content=chunk.content,
                    score=similarity,
                    metadata=chunk.metadata if query.include_metadata else {}
                )
                results.append(result)

        # Сортировка по score
        results.sort(key=lambda x: x.score, reverse=True)
        return results

    async def _sparse_search(
        self,
        query_text: str,
        query: SearchQuery
    ) -> List[SearchResult]:
        """Sparse (keyword) поиск"""
        results = []
        query_words = set(query_text.lower().split())

        for chunk in self._chunks.values():
            chunk_words = set(chunk.content.lower().split())

            # BM25-подобный scoring (упрощенный)
            intersection = query_words.intersection(chunk_words)
            if intersection:
                score = len(intersection) / len(query_words)

                if score >= query.similarity_threshold:
                    result = SearchResult(
                        chunk_id=chunk.chunk_id,
                        document_id=chunk.document_id,
                        content=chunk.content,
                        score=score,
                        metadata=chunk.metadata if query.include_metadata else {}
                    )
                    results.append(result)

        results.sort(key=lambda x: x.score, reverse=True)
        return results

    async def _hybrid_search(
        self,
        query_embedding: List[float],
        query_text: str,
        query: SearchQuery
    ) -> List[SearchResult]:
        """Гибридный поиск (dense + sparse)"""
        # Получение результатов от обеих стратегий
        dense_results = await self._dense_search(query_embedding, query)
        sparse_results = await self._sparse_search(query_text, query)

        # Объединение и ребалансировка scores
        combined_results = {}

        # Добавление dense результатов
        for result in dense_results:
            combined_results[result.chunk_id] = result
            result.score *= 0.7  # Вес для dense поиска

        # Добавление sparse результатов
        for result in sparse_results:
            if result.chunk_id in combined_results:
                # Комбинирование scores
                combined_results[result.chunk_id].score += result.score * 0.3  # Вес для sparse поиска
            else:
                result.score *= 0.3
                combined_results[result.chunk_id] = result

        # Сортировка по комбинированному score
        final_results = list(combined_results.values())
        final_results.sort(key=lambda x: x.score, reverse=True)

        return final_results

    async def _graph_enhanced_search(
        self,
        query_embedding: List[float],
        query_text: str,
        query: SearchQuery
    ) -> List[SearchResult]:
        """Graph-enhanced поиск"""
        # Начинаем с гибридного поиска
        initial_results = await self._hybrid_search(query_embedding, query_text, query)

        # Расширение через граф связей (упрощенная версия)
        enhanced_results = initial_results.copy()

        for result in initial_results[:5]:  # Берем топ-5 результатов
            # Поиск связанных чанков из того же документа
            related_chunks = [
                chunk for chunk in self._chunks.values()
                if chunk.document_id == result.document_id and chunk.chunk_id != result.chunk_id
            ]

            for related_chunk in related_chunks[:2]:  # Максимум 2 связанных чанка
                if related_chunk.embedding:
                    similarity = self._cosine_similarity(query_embedding, related_chunk.embedding)
                    if similarity >= query.similarity_threshold * 0.8:  # Пониженный порог
                        enhanced_result = SearchResult(
                            chunk_id=related_chunk.chunk_id,
                            document_id=related_chunk.document_id,
                            content=related_chunk.content,
                            score=similarity * 0.8,  # Пониженный score для связанных
                            metadata=related_chunk.metadata if query.include_metadata else {}
                        )
                        enhanced_results.append(enhanced_result)

        # Удаление дубликатов и сортировка
        unique_results = {r.chunk_id: r for r in enhanced_results}.values()
        final_results = list(unique_results)
        final_results.sort(key=lambda x: x.score, reverse=True)

        return final_results

    async def _semantic_similarity_search(
        self,
        query_embedding: List[float],
        query: SearchQuery
    ) -> List[SearchResult]:
        """Семантический поиск по сходству"""
        return await self._dense_search(query_embedding, query)

    async def _rerank_results(
        self,
        query_text: str,
        results: List[SearchResult]
    ) -> List[SearchResult]:
        """Cross-encoder reranking результатов"""
        # Заглушка для cross-encoder
        # В реальности использовать модель типа cross-encoder/ms-marco-MiniLM-L-6-v2

        reranked_results = []

        for result in results:
            # Простой reranking на основе точного совпадения фраз
            exact_matches = sum(1 for word in query_text.lower().split()
                              if word in result.content.lower())

            # Корректировка score
            rerank_boost = exact_matches * 0.1
            result.score = min(1.0, result.score + rerank_boost)

            reranked_results.append(result)

        reranked_results.sort(key=lambda x: x.score, reverse=True)
        return reranked_results

    async def _generate_highlights(self, query_text: str, content: str) -> List[str]:
        """Генерация выделенных фрагментов"""
        highlights = []
        query_words = query_text.lower().split()

        sentences = content.split(". ")
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(word in sentence_lower for word in query_words):
                # Выделение найденных слов
                highlighted = sentence
                for word in query_words:
                    if word in sentence_lower:
                        highlighted = highlighted.replace(word, f"**{word}**")
                        highlighted = highlighted.replace(word.capitalize(), f"**{word.capitalize()}**")

                highlights.append(highlighted)

                if len(highlights) >= 3:  # Максимум 3 highlight
                    break

        return highlights

    async def _aggregate_content(self, results: List[SearchResult]) -> str:
        """Агрегация содержимого результатов"""
        if not results:
            return ""

        # Объединение топ-3 результатов
        top_results = results[:3]
        aggregated = "\n\n".join([f"[{i+1}] {result.content}" for i, result in enumerate(top_results)])

        return aggregated

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Вычисление cosine similarity между векторами"""
        if not vec1 or not vec2:
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    async def _calculate_file_hash(self, file_path: str) -> str:
        """Вычисление хэша файла"""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""

    async def _get_cached_document(self, file_hash: str) -> Optional[ProcessedDocument]:
        """Получение документа из кэша по хэшу"""
        for doc in self._documents.values():
            if doc.file_hash == file_hash:
                return doc
        return None

    def _generate_search_cache_key(self, query: SearchQuery) -> str:
        """Генерация ключа кэша для поиска"""
        cache_data = {
            "query_text": query.query_text,
            "strategy": query.strategy.value,
            "filters": query.filters,
            "limit": query.limit,
            "similarity_threshold": query.similarity_threshold
        }
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_string.encode()).hexdigest()

    async def _get_cached_search(self, cache_key: str) -> Optional[SearchResponse]:
        """Получение результата поиска из кэша"""
        cache_entry = self._search_cache.get(cache_key)
        if cache_entry:
            # Обновление статистики доступа
            cache_entry.access_count += 1
            cache_entry.last_accessed = datetime.utcnow()

            # Проверка актуальности (кэш действителен 1 час)
            age = (datetime.utcnow() - cache_entry.created_at).total_seconds()
            if age < 3600:  # 1 час
                response = cache_entry.content
                response.cache_hit = True
                return response

        return None

    async def _cache_search_result(self, cache_key: str, response: SearchResponse) -> None:
        """Кэширование результата поиска"""
        cache_entry = CacheEntry(
            cache_key=cache_key,
            content=response
        )
        self._search_cache[cache_key] = cache_entry

        # Очистка старых записей кэша (простая LRU)
        if len(self._search_cache) > 1000:
            # Удаление 10% самых старых записей
            sorted_entries = sorted(
                self._search_cache.items(),
                key=lambda x: x[1].last_accessed
            )
            for key, _ in sorted_entries[:100]:
                del self._search_cache[key]

    def _update_processing_stats(self, document_type: DocumentType) -> None:
        """Обновление статистики обработки"""
        key = f"processed_{document_type.value}"
        self._processing_stats[key] = self._processing_stats.get(key, 0) + 1

    def _update_search_stats(self, strategy: SearchStrategy) -> None:
        """Обновление статистики поиска"""
        key = f"search_{strategy.value}"
        self._search_stats[key] = self._search_stats.get(key, 0) + 1

    async def _log_document_processing(
        self,
        document: ProcessedDocument,
        user_id: str,
        cache_hit: bool = False
    ) -> None:
        """Логирование обработки документа"""
        await self._log_audit_event(
            user_id=user_id,
            action="document_processed",
            payload={
                "document_id": document.document_id,
                "document_type": document.document_type.value,
                "chunks_count": len(document.chunks),
                "content_length": len(document.content),
                "cache_hit": cache_hit,
                "processing_time": document.processing_stats.get("processing_time", 0)
            }
        )

    async def _log_search(
        self,
        query: SearchQuery,
        response: SearchResponse,
        user_id: str,
        cache_hit: bool = False
    ) -> None:
        """Логирование поиска"""
        await self._log_audit_event(
            user_id=user_id,
            action="search_performed",
            payload={
                "query_id": query.query_id,
                "strategy": query.strategy.value,
                "results_count": len(response.results),
                "search_time": response.search_time,
                "cache_hit": cache_hit
            }
        )

    async def _log_embedding_generation(
        self,
        request: EmbeddingRequest,
        count: int,
        user_id: str
    ) -> None:
        """Логирование генерации эмбеддингов"""
        await self._log_audit_event(
            user_id=user_id,
            action="embeddings_generated",
            payload={
                "request_id": request.request_id,
                "texts_count": len(request.texts),
                "embeddings_count": count,
                "model": request.model
            }
        )

    async def _log_processing_error(self, file_path: str, user_id: str, error: Exception) -> None:
        """Логирование ошибки обработки"""
        await self._log_audit_event(
            user_id=user_id,
            action="processing_error",
            payload={
                "file_path": file_path,
                "error_type": type(error).__name__,
                "error_message": str(error)
            }
        )

    async def _log_search_error(self, query: SearchQuery, user_id: str, error: Exception) -> None:
        """Логирование ошибки поиска"""
        await self._log_audit_event(
            user_id=user_id,
            action="search_error",
            payload={
                "query_id": query.query_id,
                "error_type": type(error).__name__,
                "error_message": str(error)
            }
        )

    async def _log_embedding_error(
        self,
        request: EmbeddingRequest,
        user_id: str,
        error: Exception
    ) -> None:
        """Логирование ошибки эмбеддинга"""
        await self._log_audit_event(
            user_id=user_id,
            action="embedding_error",
            payload={
                "request_id": request.request_id,
                "error_type": type(error).__name__,
                "error_message": str(error)
            }
        )

    async def _log_audit_event(
        self,
        user_id: str,
        action: str,
        payload: Dict[str, Any]
    ) -> None:
        """Централизованное логирование audit событий"""
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            user_id=user_id,
            thread_id=f"rag_pipeline_agent_{user_id}",
            source="rag_pipeline_agent",
            action=action,
            payload=payload,
            tags=["rag_pipeline_agent", "search", "embeddings"]
        )

        await self.memory.alog_audit(event)

    async def get_stats(self) -> Dict[str, Any]:
        """Получение статистики RAGPipelineAgent"""
        return {
            "processing_stats": self._processing_stats.copy(),
            "search_stats": self._search_stats.copy(),
            "total_documents": len(self._documents),
            "total_chunks": len(self._chunks),
            "embeddings_cached": len(self._embeddings_cache),
            "search_cache_size": len(self._search_cache),
            "cache_hit_rate": self._calculate_cache_hit_rate()
        }

    def _calculate_cache_hit_rate(self) -> float:
        """Расчет hit rate кэша"""
        if not self._search_cache:
            return 0.0

        total_accesses = sum(entry.access_count for entry in self._search_cache.values())
        total_entries = len(self._search_cache)

        if total_entries == 0:
            return 0.0

        return min(1.0, total_accesses / total_entries)

    async def get_document(self, document_id: str) -> Optional[ProcessedDocument]:
        """Получение обработанного документа"""
        return self._documents.get(document_id)

    async def get_chunk(self, chunk_id: str) -> Optional[DocumentChunk]:
        """Получение чанка"""
        return self._chunks.get(chunk_id)