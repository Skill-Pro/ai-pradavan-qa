import pytest

if __name__ == "__main__":
    pytest.main([
        "tests",  # папка с тестами
        "--html=reports/report.html",
        "--self-contained-html"
    ])
