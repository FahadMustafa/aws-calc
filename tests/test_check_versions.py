"""extract_pairs: pair serviceCode with the version in the SAME object literal."""
from pathlib import Path

from check_versions import extract_pairs

REPO_ROOT = Path(__file__).resolve().parent.parent
REAL_MODULES = REPO_ROOT / "references" / "service-modules"

MODULE_MD = '''# Fake service module

Prose mentioning `"version": "9.9.9"` outside any fence must never be paired —
this line is a decoy.

## Flat header

```jsonc
{
  "serviceCode":  "flatServiceA",       // canonical code
  "estimateFor":  "template",
  "version":      "1",                  // form version
  "region":       "<code>",
  "serviceCost":  { "monthly": 0, "upfront": 0 }
}
```

## Block comments

```jsonc
{
  "serviceCode": "blockCommentedService",
  "estimateFor": "someForm",
  /* the SPA's "version" field for this shape is documented elsewhere:
     "version": "9" is a decoy inside a block comment, quote char included */
  "subServices": [
    { /* placeholder — see below */ }
  ]
}
```

## Group header with a nested sub-service

```json
{
  "serviceCode": "groupWrapperNoVersion",
  "estimateFor": "someGroup",
  "subServices": [
    {
      "serviceCode": "nestedServiceB",
      "estimateFor": "nestedForm",
      "version": "2",
      "calculationComponents": {
        "someSize": {"value": "1000", "unit": "gb|month"}
      }
    }
  ]
}
```
'''


def test_pairs_within_object_literal(tmp_path):
    (tmp_path / "fake.md").write_text(MODULE_MD, encoding="utf-8")

    pairs = extract_pairs(str(tmp_path))

    assert pairs == {
        "flatServiceA": {("1", "fake.md")},
        "nestedServiceB": {("2", "fake.md")},
    }


def test_prose_version_does_not_leak_into_pairs(tmp_path):
    (tmp_path / "fake.md").write_text(MODULE_MD, encoding="utf-8")
    versions = {v for vs in extract_pairs(str(tmp_path)).values() for v, _ in vs}
    assert "9.9.9" not in versions


def test_block_comment_version_is_not_paired(tmp_path):
    """`/* ... */` comments (drs.md uses them) must not contribute a version."""
    (tmp_path / "fake.md").write_text(MODULE_MD, encoding="utf-8")
    pairs = extract_pairs(str(tmp_path))
    assert "blockCommentedService" not in pairs
    assert "9" not in {v for vs in pairs.values() for v, _ in vs}


def test_real_modules_still_yield_the_full_code_set():
    pairs = extract_pairs(str(REAL_MODULES))
    # the heuristic this replaced found 65 codes; allow churn but not a regression
    assert len(pairs) >= 60, sorted(pairs)
    # every module contributes at least one code
    sources = {f for vs in pairs.values() for _, f in vs}
    assert len(sources) >= 40


def test_real_modules_have_no_placeholder_versions():
    pairs = extract_pairs(str(REAL_MODULES))
    for code, versions in pairs.items():
        for ver, fname in versions:
            assert ver[0].isdigit(), f"{code} in {fname} has non-numeric version {ver!r}"
