"""Build an explicit source-only distribution; exclude credentials and runtime outputs."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "collector.py", "emailer.py", "summarizer.py", "quality_check.py",
    "terraform_actions.py", "requirements.txt", "requirements-dev.txt",
    ".coveragerc", "README.md", "LICENSE",
)
PATTERNS = (
    "finops_agent/*.py", "tests/test_*.py", "scripts/*.py",
    "terraform/*.tf", "terraform/.terraform.lock.hcl",
    "terraform/terraform.tfvars.example", "docs/knowledge/*.py",
    "docs/knowledge/article/*.txt", "docs/knowledge/cards/*.jsonl",
    "docs/knowledge/chunks/*.jsonl", "docs/knowledge/index/*.faiss",
    "docs/knowledge/eval/*.md",
)


def build_bundle(destination=None):
    destination = Path(destination) if destination else ROOT / "dist" / "finops-agent.zip"
    destination.parent.mkdir(parents=True, exist_ok=True)
    paths = {ROOT / name for name in FILES}
    for pattern in PATTERNS:
        paths.update(ROOT.glob(pattern))
    with ZipFile(destination, "w", ZIP_DEFLATED) as bundle:
        for path in sorted(paths):
            bundle.write(path, path.relative_to(ROOT).as_posix())
    return destination


if __name__ == "__main__":
    print(build_bundle())
