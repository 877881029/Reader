from reader.version import product_version


def test_product_version_reads_repo_version_file() -> None:
    assert product_version() == "0.1.0"
