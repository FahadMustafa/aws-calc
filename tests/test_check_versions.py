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


# --- live-version cache + --codes filter -------------------------------------

import json
from datetime import datetime, timedelta, timezone

import pytest

import check_versions


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    """Point the live-version cache at a tmp dir so no test touches ~/.cache."""
    d = tmp_path / "cache"
    d.mkdir()
    monkeypatch.setenv("AWS_CALC_CACHE", str(d))
    return d


def _write_cache(cache_dir, entries):
    (cache_dir / "live-versions.json").write_text(json.dumps(entries), encoding="utf-8")


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def test_cache_hit_avoids_fetch(cache_dir, monkeypatch):
    _write_cache(cache_dir, {"svcA": {"version": "3", "fetched": _iso(datetime.now(timezone.utc))}})
    calls = []
    monkeypatch.setattr(check_versions, "fetch_live_version", lambda c: calls.append(c) or (c, "x", None))

    live = check_versions.resolve_live_versions(["svcA"])

    assert calls == []
    assert live == {"svcA": ("3", None)}


def test_stale_cache_entry_is_refetched(cache_dir, monkeypatch):
    old = datetime.now(timezone.utc) - timedelta(hours=25)
    _write_cache(cache_dir, {"svcA": {"version": "3", "fetched": _iso(old)}})
    monkeypatch.setattr(check_versions, "fetch_live_version", lambda c: (c, "4", None))

    live = check_versions.resolve_live_versions(["svcA"])

    assert live == {"svcA": ("4", None)}
    stored = json.loads((cache_dir / "live-versions.json").read_text())
    assert stored["svcA"]["version"] == "4"


def test_refresh_bypasses_fresh_cache(cache_dir, monkeypatch):
    _write_cache(cache_dir, {"svcA": {"version": "3", "fetched": _iso(datetime.now(timezone.utc))}})
    monkeypatch.setattr(check_versions, "fetch_live_version", lambda c: (c, "5", None))

    live = check_versions.resolve_live_versions(["svcA"], refresh=True)

    assert live == {"svcA": ("5", None)}
    assert json.loads((cache_dir / "live-versions.json").read_text())["svcA"]["version"] == "5"


def test_no_live_def_is_cached_as_null_and_not_refetched(cache_dir, monkeypatch):
    calls = []

    def fake(code):
        calls.append(code)
        return code, None, "no-live-def"

    monkeypatch.setattr(check_versions, "fetch_live_version", fake)
    assert check_versions.resolve_live_versions(["svcA"]) == {"svcA": (None, "no-live-def")}

    assert json.loads((cache_dir / "live-versions.json").read_text())["svcA"]["version"] is None
    assert check_versions.resolve_live_versions(["svcA"]) == {"svcA": (None, "no-live-def")}
    assert calls == ["svcA"]  # only the first run fetched


def test_transient_errors_are_not_cached(cache_dir, monkeypatch):
    monkeypatch.setattr(check_versions, "fetch_live_version", lambda c: (c, None, "http 500"))

    live = check_versions.resolve_live_versions(["svcA"])

    assert live == {"svcA": (None, "http 500")}
    assert "svcA" not in json.loads((cache_dir / "live-versions.json").read_text())


def test_corrupt_cache_is_ignored(cache_dir, monkeypatch):
    (cache_dir / "live-versions.json").write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(check_versions, "fetch_live_version", lambda c: (c, "7", None))

    assert check_versions.resolve_live_versions(["svcA"]) == {"svcA": ("7", None)}


# --- main(): --codes filter and stale_modules --------------------------------

TWO_MODULES = {
    "alpha.md": '```json\n{"serviceCode": "svcA", "estimateFor": "f", "version": "1"}\n```\n',
    "beta.md": '```json\n{"serviceCode": "svcB", "estimateFor": "f", "version": "2"}\n```\n',
}


@pytest.fixture
def modules(tmp_path):
    d = tmp_path / "modules"
    d.mkdir()
    for name, body in TWO_MODULES.items():
        (d / name).write_text(body, encoding="utf-8")
    return d


def test_codes_filter_narrows_rows(cache_dir, modules, monkeypatch, capsys):
    monkeypatch.setattr(check_versions, "fetch_live_version", lambda c: (c, "1", None))

    rc = check_versions.main(["--modules", str(modules), "--json", "--codes", "svcA"])

    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert [r["serviceCode"] for r in out["rows"]] == ["svcA"]


def test_unknown_code_in_filter_is_an_error(cache_dir, modules, monkeypatch, capsys):
    monkeypatch.setattr(check_versions, "fetch_live_version", lambda c: (c, "1", None))

    rc = check_versions.main(["--modules", str(modules), "--json", "--codes", "svcZZ"])

    assert rc == 2


def test_stale_modules_lists_drifted_module_files(cache_dir, modules, monkeypatch, capsys):
    # svcA pinned at 1, live 9 -> DRIFT; svcB pinned at 2, live 2 -> ok
    live = {"svcA": "9", "svcB": "2"}
    monkeypatch.setattr(check_versions, "fetch_live_version", lambda c: (c, live[c], None))

    rc = check_versions.main(["--modules", str(modules), "--json"])

    out = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert out["drift"] == 1
    assert out["errors"] == 0
    assert out["stale_modules"] == ["alpha.md"]
    assert len(out["rows"]) == 2


def test_stale_modules_empty_when_clean(cache_dir, modules, monkeypatch, capsys):
    live = {"svcA": "1", "svcB": "2"}
    monkeypatch.setattr(check_versions, "fetch_live_version", lambda c: (c, live[c], None))

    rc = check_versions.main(["--modules", str(modules), "--json"])

    assert rc == 0
    assert json.loads(capsys.readouterr().out)["stale_modules"] == []


# --- HTTP status classification ----------------------------------------------

import email.message
import io
import urllib.error
import urllib.request


def _http_error(status, body=b""):
    return urllib.error.HTTPError(
        "https://example.invalid/x", status, "err", email.message.Message(), io.BytesIO(body)
    )


def _raise_on_fetch(monkeypatch, exc):
    def boom(req, timeout=None):
        raise exc

    monkeypatch.setattr(check_versions.urllib.request, "urlopen", boom)


ACCESS_DENIED = b'<?xml version="1.0"?><Error><Code>AccessDenied</Code></Error>'
CF_BLOCKED = b"<HTML><HEAD>ERROR: The request could not be satisfied</HEAD></HTML>"


def test_404_is_no_live_def(monkeypatch):
    _raise_on_fetch(monkeypatch, _http_error(404))
    assert check_versions.fetch_live_version("svcA") == ("svcA", None, "no-live-def")


def test_s3_access_denied_403_is_no_live_def(monkeypatch):
    """The CDN's "this definition does not exist" is a 403 + AccessDenied XML."""
    _raise_on_fetch(monkeypatch, _http_error(403, ACCESS_DENIED))
    assert check_versions.fetch_live_version("svcA") == ("svcA", None, "no-live-def")


def test_cloudfront_403_is_a_transient_error_not_no_live_def(monkeypatch):
    """A throttled/blocked 403 must never read as "not drift"."""
    _raise_on_fetch(monkeypatch, _http_error(403, CF_BLOCKED))
    assert check_versions.fetch_live_version("svcA") == ("svcA", None, "http 403")


def test_cloudfront_403_is_not_cached(cache_dir, monkeypatch):
    _raise_on_fetch(monkeypatch, _http_error(403, CF_BLOCKED))

    live = check_versions.resolve_live_versions(["svcA"])

    assert live == {"svcA": (None, "http 403")}
    assert json.loads((cache_dir / "live-versions.json").read_text()) == {}


# --- cache merge on refresh ---------------------------------------------------

def test_refresh_preserves_unrelated_cached_codes(cache_dir, monkeypatch):
    """`--refresh --codes svcA` must not evict svcB from the shared cache file."""
    b_entry = {"version": "2", "fetched": _iso(datetime.now(timezone.utc))}
    _write_cache(cache_dir, {"svcA": {"version": "1", "fetched": _iso(datetime.now(timezone.utc))}, "svcB": b_entry})
    monkeypatch.setattr(check_versions, "fetch_live_version", lambda c: (c, "9", None))

    live = check_versions.resolve_live_versions(["svcA"], refresh=True)

    assert live == {"svcA": ("9", None)}
    stored = json.loads((cache_dir / "live-versions.json").read_text())
    assert stored["svcA"]["version"] == "9"
    assert stored["svcB"] == b_entry


def test_future_dated_entry_is_refetched(cache_dir, monkeypatch):
    """Clock skew or a hand-edited file must not pin a stale version indefinitely."""
    ahead = datetime.now(timezone.utc) + timedelta(days=30)
    _write_cache(cache_dir, {"svcA": {"version": "1", "fetched": _iso(ahead)}})
    monkeypatch.setattr(check_versions, "fetch_live_version", lambda c: (c, "9", None))

    assert check_versions.resolve_live_versions(["svcA"]) == {"svcA": ("9", None)}
