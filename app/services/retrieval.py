import re
from pathlib import Path

from app.core.schemas import Citation, RetrievalResult


class LocalVaultRetriever:
    def __init__(self, vault_path: str, top_k: int = 4) -> None:
        self.vault_path = Path(vault_path)
        self.top_k = top_k

    def retrieve(self, query: str) -> RetrievalResult:
        terms = set(re.findall(r"[\w-]+", query.lower()))
        if not terms:
            return RetrievalResult(status="empty")
        if not self.vault_path.is_dir():
            return RetrievalResult(status="error")

        ranked: list[tuple[int, Path, str]] = []
        for path in self.vault_path.rglob("*.md"):
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            score = sum(text.lower().count(term) for term in terms)
            if score:
                ranked.append((score, path, text))

        ranked.sort(key=lambda item: (-item[0], str(item[1])))
        selected = ranked[: self.top_k]
        if not selected:
            return RetrievalResult(status="empty")

        context = "\n\n".join(text[:6000] for _, _, text in selected)
        citations = [
            Citation(source=str(path), excerpt=text[:240].replace("\n", " "))
            for _, path, text in selected
        ]
        return RetrievalResult(
            status="success",
            context=context,
            citations=citations,
            sources=[str(path) for _, path, _ in selected],
        )
