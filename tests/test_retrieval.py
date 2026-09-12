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
