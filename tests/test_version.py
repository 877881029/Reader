from reader.version import product_version


def test_product_version_reads_repo_version_file() -> None:
    from pathlib import Path

    version_file = Path(__file__).resolve().parents[1] / "VERSION"
    assert product_version() == version_file.read_text(encoding="utf-8").strip()
