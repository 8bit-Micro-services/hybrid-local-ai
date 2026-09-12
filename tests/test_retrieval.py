from pathlib import Path

from app.services.retrieval import LocalVaultRetriever


def test_retriever_matches_words_and_orders_ties_by_path(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "b.md").write_text("Local AI notes", encoding="utf-8")
    (vault / "a.md").write_text("Local AI notes", encoding="utf-8")

    result = LocalVaultRetriever(str(vault), top_k=2).retrieve("local")

    assert result.status == "success"
    assert result.sources == [str(vault / "a.md"), str(vault / "b.md")]


def test_retriever_reports_missing_vault(tmp_path: Path):
    result = LocalVaultRetriever(str(tmp_path / "missing")).retrieve("hello")

    assert result.status == "error"


def test_retriever_returns_empty_for_blank_query(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()

    assert LocalVaultRetriever(str(vault)).retrieve("   ").status == "empty"


def test_retriever_chunks_by_markdown_headers(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    doc = """# Introduction
This is the intro section about machine learning.

## Architecture
FastAPI connects to Ollama model locally.

## Deployment
Docker compose manages the services.
"""
    (vault / "doc.md").write_text(doc, encoding="utf-8")

    retriever = LocalVaultRetriever(str(vault), top_k=1)
    result = LocalVaultRetriever(str(vault), top_k=1).retrieve("architecture")

    assert result.status == "success"
    assert "FastAPI connects to Ollama" in result.context
    assert "[Architecture]" in result.context
    assert len(result.citations) == 1


def test_retriever_uses_cache_and_updates_on_modification(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    file_path = vault / "note.md"
    file_path.write_text("initial content version 1", encoding="utf-8")

    retriever = LocalVaultRetriever(str(vault))
    res1 = retriever.retrieve("version")
    assert "version 1" in res1.context

    # Update file content
    file_path.write_text("updated content version 2", encoding="utf-8")
    res2 = retriever.retrieve("version")
    assert "version 2" in res2.context
