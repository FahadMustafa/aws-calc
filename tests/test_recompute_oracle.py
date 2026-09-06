"""Offline tests for the recompute oracle.

Every catalog read is served from `tests/fixtures/catalogs/`, which holds the real
calculator.aws artifacts trimmed to the region (`US East (Ohio)`) and keys these
tests exercise. The single network seam is `catalog.fetch_json`, monkeypatched
here; a fixture miss raises rather than silently falling through to the network.

Fixture filenames are `catalog.cache_key_for_url(url)`, so the same function names
the on-disk cache entry and the committed fixture — no second mapping to drift.
"""
import json
from pathlib import Path

import pytest

import catalog
import recompute_oracle as oracle

FIXTURES = Path(__file__).parent / "fixtures" / "catalogs"
REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_BODY = REPO_ROOT / "references" / "examples" / "sample-saveas-body.json"
OHIO = "US East (Ohio)"


@pytest.fixture(autouse=True)
def offline_catalog(monkeypatch):
    """Serve every catalog fetch from a committed fixture; never touch the network."""
    def fake_fetch_json(url, *, refresh=False, cache_name=None):
        path = FIXTURES / catalog.cache_key_for_url(url)
        if not path.exists():
            raise catalog.CatalogError(f"no fixture for {url} (expected {path.name})")
        return json.loads(path.read_text())

    monkeypatch.setattr(catalog, "fetch_json", fake_fetch_json)
    return fake_fetch_json


@pytest.fixture(scope="module")
def sample_body():
    return json.loads(SAMPLE_BODY.read_text())


def row_for(rows, service_code, index=0):
    matching = [r for r in rows if r["serviceCode"] == service_code]
    assert matching, f"no row for {service_code} in {[r['serviceCode'] for r in rows]}"
    return matching[index]


# --------------------------------------------------------------------------- #
# catalog helpers                                                               #
# --------------------------------------------------------------------------- #


def test_cache_key_is_derived_from_the_url_path_only():
    assert catalog.cache_key_for_url(
        "https://d1qsjq9pzbk1k6.cloudfront.net/data/ec2Enhancement/en_US.json"
    ) == "data_ec2Enhancement_en_US.json"


def test_mapping_definition_urls_substitute_the_currency_placeholder():
    form_def = json.loads((FIXTURES / "data_awsS3DataTransfer_en_US.json").read_text())
    urls = catalog.mapping_definition_urls(form_def)
    assert urls["datatransfer-calc"] == (
        "https://calculator.aws/pricing/2.0/meteredUnitMaps/datatransfer/USD/current/datatransfer-calc.json"
    )
    assert "[currency]" not in json.dumps(urls)


def test_region_display_name_fails_loud_on_an_unknown_region():
    assert catalog.region_display_name("us-east-2") == OHIO
    with pytest.raises(catalog.CatalogError):
        catalog.region_display_name("xx-nowhere-9")


def test_price_of_raises_rather_than_returning_zero_for_a_missing_key():
    prices = {"a": {"price": "0.5"}}
    assert catalog.price_of(prices, "a") == 0.5
    with pytest.raises(catalog.CatalogError):
        catalog.price_of(prices, "missing")


# --------------------------------------------------------------------------- #
# the sample body — the reconciliation that matters                             #
# --------------------------------------------------------------------------- #


def test_sample_ec2_on_demand_line_recomputes_within_one_percent(sample_body):
    """t3.small Windows OD + 500 GB gp3 in us-east-2, stored at $68.62.

    0.0392/hr x 730 x 100% x 1 = $28.616 compute, + 0.08 x 500 = $40.00 gp3.
    """
    rows = oracle.evaluate(sample_body)
    row = row_for(rows, "ec2Enhancement", 0)
    assert row["stored"] == 68.62
    assert row["recomputed"] == pytest.approx(68.616, abs=0.001)
    assert abs(row["delta_pct"]) < 1.0


def test_sample_ec2_line_flags_the_unmodelled_snapshot_rather_than_guessing(sample_body):
    rows = oracle.evaluate(sample_body)
    row = row_for(rows, "ec2Enhancement", 0)
    assert any("snapshot not modelled" in note for note in row["notes"])


def test_sample_reserved_ec2_line_reports_no_oracle(sample_body):
    """The r5.large RI 3yr No Upfront line is uncompared, not silently passed."""
    rows = oracle.evaluate(sample_body)
    row = row_for(rows, "ec2Enhancement", 1)
    assert row["recomputed"] is None
    assert row["delta_pct"] is None
    assert any("reserved" in note.lower() for note in row["notes"])


def test_sample_s3_standard_line_recomputes_within_one_percent(sample_body):
    """1000 GB in the first (50 TB) band at $0.023/GB-mo = $23.00, stored $23."""
    rows = oracle.evaluate(sample_body)
    row = row_for(rows, "amazonS3Standard")
    assert row["stored"] == 23
    assert row["recomputed"] == pytest.approx(23.0, abs=0.001)
    assert abs(row["delta_pct"]) < 1.0


def test_sample_s3_data_transfer_line_reports_the_missing_destination(sample_body):
    """100 TB outbound with an empty toRegion is genuinely $0 — the SPA's own trap."""
    rows = oracle.evaluate(sample_body)
    row = row_for(rows, "awsS3DataTransfer")
    assert row["stored"] == 0
    assert row["recomputed"] == 0.0
    assert row["delta_pct"] == 0.0
    assert any("no destination" in note for note in row["notes"])


def test_unregistered_service_codes_report_no_oracle(sample_body):
    rows = oracle.evaluate(sample_body)
    rds = row_for(rows, "amazonRDSPostgreSQLDB")
    assert rds["recomputed"] is None
    assert rds["notes"] == ["no oracle for serviceCode 'amazonRDSPostgreSQLDB'"]


def test_group_sub_services_are_walked_and_labelled(sample_body):
    rows = oracle.evaluate(sample_body)
    codes = [r["serviceCode"] for r in rows]
    # The S3 and VPC groups contribute their sub-services, not the group envelope.
    assert "amazonSimpleStorageServiceGroup" not in codes
    assert {"amazonS3Standard", "awsS3DataTransfer", "vpnConnectionVpc", "transitGatewayVpc"} <= set(codes)
    assert row_for(rows, "amazonS3Standard")["key"].startswith("amazonSimpleStorageServiceGroup-")


def test_sample_body_has_no_breaches_and_the_cli_exits_zero(sample_body, capsys, monkeypatch, offline_catalog):
    rows = oracle.evaluate(sample_body)
    assert oracle.breaches(rows, oracle.DEFAULT_TOLERANCE_PCT) == []
    monkeypatch.setattr(catalog, "fetch_json", offline_catalog)
    assert oracle.main([str(SAMPLE_BODY)]) == 0
    out = capsys.readouterr().out
    assert "recomputed" in out and "68.62" in out


def test_json_output_is_machine_readable(capsys):
    assert oracle.main([str(SAMPLE_BODY), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["tolerance_pct"] == 1.0
    assert any(r["serviceCode"] == "amazonS3Standard" for r in payload["rows"])


def test_a_wrong_stored_value_breaches_and_exits_one(tmp_path, sample_body, capsys):
    body = json.loads(json.dumps(sample_body))
    key = next(k for k in body["services"] if k.startswith("ec2Enhancement-"))
    body["services"][key]["serviceCost"]["monthly"] = 100.0
    path = tmp_path / "body.json"
    path.write_text(json.dumps(body))
    assert oracle.main([str(path)]) == 1
    assert "outside" in capsys.readouterr().out


def test_missing_body_file_exits_two(tmp_path, capsys):
    assert oracle.main([str(tmp_path / "nope.json")]) == 2


# --------------------------------------------------------------------------- #
# recomputers exercised directly                                                #
# --------------------------------------------------------------------------- #


def test_s3_standard_walks_all_three_bands():
    """600 TB: 50 TB @ .023 + 450 TB @ .022 + 100 TB @ .021."""
    item = {"calculationComponents": {"s3StandardStorageSize": {"value": "614400", "unit": "gb|month"}}}
    expected = 51200 * 0.023 + (512000 - 51200) * 0.022 + (614400 - 512000) * 0.021
    assert oracle.recompute_s3_standard(item, OHIO).recomputed == pytest.approx(expected)


def test_s3_outbound_to_external_walks_the_datatransfer_bands():
    """100 TB out: 10 TB @ .09 + 40 TB @ .085 + 50 TB of the 100 TB band @ .07."""
    item = {"calculationComponents": {"dataTransfer": {"value": [
        {"entryType": "INBOUND", "value": "100", "unit": "tb_month", "fromRegion": ""},
        {"entryType": "OUTBOUND", "value": "100", "unit": "tb_month", "toRegion": "External"},
    ]}}}
    expected = 10240 * 0.09 + 40960 * 0.085 + (102400 - 51200) * 0.07
    result = oracle.recompute_s3_data_transfer(item, OHIO)
    assert result.recomputed == pytest.approx(expected)
    assert result.notes == []


def test_inter_region_outbound_is_excluded_with_a_note():
    item = {"calculationComponents": {"dataTransfer": {"value": [
        {"entryType": "OUTBOUND", "value": "10", "unit": "tb_month", "toRegion": "us-west-2"},
    ]}}}
    result = oracle.recompute_s3_data_transfer(item, OHIO)
    assert result.recomputed == 0.0
    assert any("inter-region" in note for note in result.notes)


def test_sqs_reproduces_the_captured_ten_dollar_estimate_minus_fair():
    """sqs.md's capture: 10M Standard ($4.00) + 10M FIFO ($5.00) + 10M Fair ($1.00).

    queueservice.json carries no Fair SKU, so the oracle refuses the line rather
    than quietly pricing two of the three queue types.
    """
    def item(fair):
        return {"calculationComponents": {
            "standardQueueRequests": {"value": "10", "unit": "perMonth"},
            "fifoQueueRequests": {"value": "10", "unit": "perMonth"},
            "fairQueueRequests": {"value": fair, "unit": "perMonth"},
            "dataTransfer": {"value": [
                {"entryType": "INBOUND", "value": "10", "unit": "tb_month", "fromRegion": ""},
                {"entryType": "OUTBOUND", "value": "10", "unit": "tb_month", "toRegion": ""},
            ]},
        }}

    without_fair = oracle.recompute_sqs(item("0"), OHIO)
    assert without_fair.recomputed == pytest.approx(9.00)  # $4 standard + $5 FIFO
    assert any("no destination" in note for note in without_fair.notes)

    with_fair = oracle.recompute_sqs(item("10"), OHIO)
    assert with_fair.recomputed is None
    assert any("fair queue" in note.lower() for note in with_fair.notes)


def test_sqs_standard_requests_cross_the_tier_boundary():
    """150,000M requests: 100,000M @ $0.40/M then 50,000M @ $0.30/M."""
    item = {"calculationComponents": {"standardQueueRequests": {"value": "150000", "unit": "perMonth"}}}
    expected = 100_000 * 0.40 + 50_000 * 0.30
    assert oracle.recompute_sqs(item, OHIO).recomputed == pytest.approx(expected)


def test_sns_standard_reproduces_the_captured_220_92():
    """sns.md's captured Standard sub-service: every dimension at 10 (M or GB)."""
    ten = {"value": "10", "unit": "millionPerMonth"}
    item = {"calculationComponents": {
        "numberOfRequests": ten,
        "numberOfHTTPNotifications": ten,
        "numberOfEmailNotifications": ten,
        "numberOfSQSNotifications": ten,
        "aws_Lambda": ten,
        "Amazon_Kinesis_Data_Firehose": ten,
        "numberOfMobilePushNotifications": ten,
        "publishAndDeliveryMessageScanning": {"value": "10", "unit": "gb|month"},
        "auditReporting": {"value": "10", "unit": "gb|month"},
        "The_amount_of_outbound_payload_data_scanned_per_month": {"value": "10", "unit": "gb|NA"},
        "simpleNotificationServiceSns_generated_23": {"value": [
            {"entryType": "INBOUND", "value": "0", "unit": "tb_month", "fromRegion": ""},
            {"entryType": "OUTBOUND", "value": "0", "unit": "tb_month", "toRegion": ""},
        ]},
    }}
    result = oracle.recompute_sns_standard(item, OHIO)
    assert result.recomputed == pytest.approx(220.92, abs=0.005)
    assert any("mobile push" in note for note in result.notes)


def test_sns_fifo_reproduces_the_captured_10_28():
    """sns.md's captured FIFO sub-service: 10M requests, 4 KB, 10 subs, 10-day retention."""
    item = {"calculationComponents": {
        "Average_message_size": {"value": "4", "unit": "kb|NA"},
        "numberOfRequests": {"value": "10", "unit": "millionPerMonth"},
        "Number_of_subscriptions": {"value": "10"},
        "retentionperiod": {"value": "10", "unit": "day"},
        "The_amount_of_outbound_payload_data_scanned_per_month": {"value": "10", "unit": "gb|NA"},
    }}
    assert oracle.recompute_sns_fifo(item, OHIO).recomputed == pytest.approx(10.28, abs=0.01)


def test_ec2_utilization_scales_the_on_demand_line():
    """ec2.md's live-verified behaviour: On-Demand does scale by utilizationValue."""
    item = {"calculationComponents": {
        "tenancy": {"value": "shared"},
        "selectedOS": {"value": "windows"},
        "instanceType": {"value": "m5.large"},
        "workload": {"value": {"workloadType": "consistent", "data": "2"}},
        "pricingStrategy": {"value": {"selectedOption": "on-demand", "utilizationValue": "50"}},
        "snapshotFrequency": {"value": "0"},
    }}
    result = oracle.recompute_ec2(item, OHIO)
    shard = json.loads((FIXTURES / catalog.cache_key_for_url(
        oracle.ec2_shard_url(OHIO, "Shared", "Windows", "Yes"))).read_text())
    hourly = next(float(r["price"]) for r in shard["regions"][OHIO].values()
                  if r["Instance Type"] == "m5.large")
    assert result.recomputed == pytest.approx(hourly * 730 * 0.5 * 2)
    assert result.notes == []


def test_ec2_rejects_an_unrecognised_os_token_instead_of_pricing_it_as_linux():
    """ec2.md: 'sles' is not accepted and silently repricing it as Linux is the bug."""
    item = {"calculationComponents": {
        "selectedOS": {"value": "sles"},
        "instanceType": {"value": "m5.large"},
        "pricingStrategy": {"value": {"selectedOption": "on-demand"}},
    }}
    result = oracle.recompute_ec2(item, OHIO)
    assert result.recomputed is None
    assert any("sles" in note for note in result.notes)


def test_ec2_reports_an_unknown_instance_type_rather_than_zero():
    item = {"calculationComponents": {
        "selectedOS": {"value": "windows"},
        "instanceType": {"value": "zz9.plural-z-alpha"},
        "pricingStrategy": {"value": {"selectedOption": "on-demand"}},
    }}
    result = oracle.recompute_ec2(item, OHIO)
    assert result.recomputed is None
    assert any("not found in ec2-calc" in note for note in result.notes)
