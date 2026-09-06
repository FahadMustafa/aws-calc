"""Every service module must carry an honest `## Coverage` table.

The table maps each configuration path the module covers to one of three
confidence labels, plus the anchor (capture file / fixture / share URL) that
backs the claim. It sits immediately after the H1 so a reader — human or
agent — sees what is actually proven before reading any formula.
"""
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MODULES_DIR = REPO_ROOT / "references" / "service-modules"

TEMPLATE_PATH = MODULES_DIR / "_template.md"
MODULE_PATHS = sorted(p for p in MODULES_DIR.glob("*.md") if p.name != "_template.md")

VALID_LABELS = {"recompute-verified", "capture-verified", "inferred"}

HEADER_ROW = "| Path | Confidence | Anchor |"


def coverage_rows(text: str) -> list[list[str]]:
    """Return the data rows of the Coverage table as split cell lists."""
    lines = text.splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.strip() == "## Coverage")
    rows = []
    seen_header = False
    for ln in lines[start + 1 :]:
        stripped = ln.strip()
        if stripped.startswith("## "):
            break
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if not seen_header:
            assert stripped == HEADER_ROW, f"unexpected table header: {stripped!r}"
            seen_header = True
            continue
        if all(set(c) <= {"-", ":"} and c for c in cells):
            continue  # separator row
        rows.append(cells)
    assert seen_header, "Coverage table header row not found"
    return rows


def test_modules_directory_is_populated():
    assert len(MODULE_PATHS) >= 42


@pytest.mark.parametrize("path", MODULE_PATHS + [TEMPLATE_PATH], ids=lambda p: p.name)
def test_module_has_coverage_section_before_any_other_heading(path: Path):
    lines = path.read_text().splitlines()
    assert lines[0].startswith("# "), "module must open with an H1"
    headings = [ln.strip() for ln in lines[1:] if ln.strip().startswith("## ")]
    assert headings, f"{path.name} has no level-2 headings"
    assert headings[0] == "## Coverage", (
        f"{path.name}: first ## heading is {headings[0]!r}, expected '## Coverage'"
    )


@pytest.mark.parametrize("path", MODULE_PATHS, ids=lambda p: p.name)
def test_coverage_table_rows_are_well_formed(path: Path):
    rows = coverage_rows(path.read_text())
    assert rows, f"{path.name}: Coverage table has no data rows"
    assert len(rows) <= 12, f"{path.name}: Coverage table has {len(rows)} rows (max 12)"
    for cells in rows:
        assert len(cells) == 3, f"{path.name}: malformed row {cells!r}"
        label = cells[1]
        assert label in VALID_LABELS, (
            f"{path.name}: confidence {label!r} not one of {sorted(VALID_LABELS)}"
        )
        assert cells[0], f"{path.name}: empty Path cell in {cells!r}"
        assert cells[2], f"{path.name}: empty Anchor cell in {cells!r}"


@pytest.mark.parametrize("path", MODULE_PATHS, ids=lambda p: p.name)
def test_coverage_anchor_files_exist(path: Path):
    """Anchors that name a repo path must point at a file that exists."""
    for cells in coverage_rows(path.read_text()):
        for match in re.findall(r"references/[\w./-]+", cells[2]):
            target = REPO_ROOT / match.rstrip(".,")
            assert target.exists(), f"{path.name}: anchor {match} does not exist"


def test_template_documents_the_coverage_table():
    text = TEMPLATE_PATH.read_text()
    assert HEADER_ROW in text
    for label in VALID_LABELS:
        assert label in text


def test_skill_refuses_inferred_paths_by_default():
    text = (REPO_ROOT / "SKILL.md").read_text()
    assert "best-effort (inferred shape)" in text
    assert "Coverage" in text
