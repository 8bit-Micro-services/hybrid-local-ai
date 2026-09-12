import re
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

from app.core.schemas import Citation, RetrievalResult


@dataclass
class DocumentChunk:
    source_path: str
    section_title: str
    content: str


class CachedFile(NamedTuple):
    mtime: float
    chunks: list[DocumentChunk]


class LocalVaultRetriever:
    def __init__(self, vault_path: str, top_k: int = 4, max_chunk_size: int = 2000) -> None:
        self.vault_path = Path(vault_path)
        self.top_k = top_k
        self.max_chunk_size = max_chunk_size
        self._cache: dict[Path, CachedFile] = {}

    def _split_into_chunks(self, path: Path, text: str) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        source_str = str(path)
        current_title = path.stem
        lines = text.splitlines()
        current_lines: list[str] = []

        for line in lines:
            if re.match(r"^#{1,4}\s+(.+)$", line.strip()):
                if current_lines:
                    chunk_text = "\n".join(current_lines).strip()
                    if chunk_text:
                        chunks.append(
                            DocumentChunk(
                                source_path=source_str,
                                section_title=current_title,
                                content=chunk_text[: self.max_chunk_size],
                            )
                        )
                    current_lines = []
                current_title = line.strip().lstrip("#").strip()
            current_lines.append(line)

        if current_lines:
            chunk_text = "\n".join(current_lines).strip()
            if chunk_text:
                chunks.append(
                    DocumentChunk(
                        source_path=source_str,
                        section_title=current_title,
                        content=chunk_text[: self.max_chunk_size],
                    )
                )

        if not chunks and text.strip():
            chunks.append(
                DocumentChunk(
                    source_path=source_str,
                    section_title=path.stem,
                    content=text.strip()[: self.max_chunk_size],
                )
            )
        return chunks

    def _load_chunks(self) -> list[DocumentChunk]:
        active_paths: set[Path] = set()
        all_chunks: list[DocumentChunk] = []

        for path in self.vault_path.rglob("*.md"):
            try:
                stat = path.stat()
            except OSError:
                continue

            active_paths.add(path)
            cached = self._cache.get(path)
            if cached is not None and cached.mtime == stat.st_mtime:
                all_chunks.extend(cached.chunks)
            else:
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                chunks = self._split_into_chunks(path, text)
                self._cache[path] = CachedFile(mtime=stat.st_mtime, chunks=chunks)
                all_chunks.extend(chunks)

        # Cleanup removed files
        for old_path in list(self._cache.keys()):
            if old_path not in active_paths:
                del self._cache[old_path]

        return all_chunks

    def retrieve(self, query: str) -> RetrievalResult:
        terms = set(re.findall(r"[\w-]+", query.lower()))
        if not terms:
            return RetrievalResult(status="empty")
        if not self.vault_path.is_dir():
            return RetrievalResult(status="error")

        chunks = self._load_chunks()
        ranked: list[tuple[float, DocumentChunk]] = []

        for chunk in chunks:
            content_lower = chunk.content.lower()
            title_lower = chunk.section_title.lower()

            matched_terms = sum(1 for term in terms if term in content_lower or term in title_lower)
            if not matched_terms:
                continue

            freq_score = sum(content_lower.count(term) for term in terms)
            title_bonus = sum(5 for term in terms if term in title_lower)
            # Distinct terms matching gives strong relevance bonus
            total_score = (matched_terms * 10.0) + freq_score + title_bonus

            ranked.append((total_score, chunk))

        ranked.sort(key=lambda item: (-item[0], item[1].source_path, item[1].section_title))
        selected = [chunk for _, chunk in ranked[: self.top_k]]
        if not selected:
            return RetrievalResult(status="empty")

        # Deduplicate sources while preserving ranking order
        unique_sources: list[str] = []
        for c in selected:
            if c.source_path not in unique_sources:
                unique_sources.append(c.source_path)

        context = "\n\n---\n\n".join(
            f"[{c.section_title}] ({c.source_path})\n{c.content}" for c in selected
        )
        citations = [
            Citation(
                source=c.source_path,
                excerpt=c.content[:240].replace("\n", " ").strip(),
            )
            for c in selected
        ]

        return RetrievalResult(
            status="success",
            context=context,
            citations=citations,
            sources=unique_sources,
        )
