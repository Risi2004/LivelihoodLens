from typing import get_args

import pytest
from fastapi.testclient import TestClient

from app import config, schemas
from app.main import create_app
from tests.fixtures import FRESH_SOURCES, TODAY, store

GALLE_BODY = {"district": "Galle", "budget_lkr": 75_000, "skills": ["sewing"], "hours": "10-20"}


def client_for(sources=None):
    return TestClient(create_app(load_store=lambda: store(sources), today=lambda: TODAY))


@pytest.fixture
def client():
    with client_for() as test_client:
        yield test_client


def messages(response):
    return [item["message"] for item in response.json()["detail"]]


def test_literals_match_config():
    assert set(get_args(schemas.Skill)) == set(config.SKILLS)
    assert list(get_args(schemas.Hours)) == config.HOURS_BUCKETS


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_districts(client):
    rows = {row["name"]: row for row in client.get("/districts").json()}
    assert rows["Galle"]["coverage_flag"] == "adequate"
    assert rows["Galle"]["is_pilot"] is True
    assert rows["Galle"]["total_businesses"] == 1000
    assert rows["Galle"]["population"] == 1_130_000
    assert rows["Monaragala"]["coverage_flag"] == "insufficient"
    assert rows["Monaragala"]["per_10k"] == pytest.approx(1.18)
    assert rows["Monaragala"]["is_pilot"] is False
    assert rows["Kalutara"]["coverage_flag"] == "low"


def test_categories(client):
    rows = {row["id"]: row for row in client.get("/categories").json()}
    assert rows["tailoring_clothing"] == {
        "id": "tailoring_clothing",
        "label": "Tailoring & clothing",
        "skills": ["sewing"],
        "cost_min_lkr": 40_000,
        "cost_max_lkr": 70_000,
    }


def test_freshness(client):
    body = client.get("/freshness").json()
    assert body["osm"] == {"date": "2026-10-30", "age_days": 3, "stale": False}
    assert body["hies"]["year"] == 2019
    assert body["placeholder"] is False


def test_freshness_reports_placeholder():
    with client_for({**FRESH_SOURCES, "placeholder": True}) as client:
        assert client.get("/freshness").json()["placeholder"] is True


def test_recommend_ok(client):
    response = client.post("/recommend", json=GALLE_BODY)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["results"][0]["category_id"] == "tailoring_clothing"
    assert body["other_options"]
    assert body["disclaimer"] == config.DISCLAIMER


def test_recommend_insufficient_data(client):
    response = client.post("/recommend", json={**GALLE_BODY, "district": "Monaragala"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "insufficient_data"
    assert body["failed_rule"] == "per_10k"
    assert body["min_required"] == 5
    assert body["suggestions"] == ["Badulla"]


@pytest.mark.parametrize("budget", [24_999, 300_001])
def test_budget_out_of_range_is_readable(client, budget):
    response = client.post("/recommend", json={**GALLE_BODY, "budget_lkr": budget})
    assert response.status_code == 422
    assert messages(response) == ["budget_lkr must be between 25,000 and 300,000"]


@pytest.mark.parametrize("budget", [25_000, 300_000])
def test_budget_limits_are_accepted(client, budget):
    assert client.post("/recommend", json={**GALLE_BODY, "budget_lkr": budget}).status_code == 200


@pytest.mark.parametrize(
    "change, expected",
    [
        ({"district": "Atlantis"}, "district must be one of the 25 official districts, not 'Atlantis'"),
        ({"budget_lkr": "lots"}, "budget_lkr must be a whole number"),
        ({"skills": "sewing"}, "skills must be a list"),
    ],
)
def test_other_bad_inputs_are_readable(client, change, expected):
    response = client.post("/recommend", json={**GALLE_BODY, **change})
    assert response.status_code == 422
    assert messages(response) == [expected]


def test_unknown_skill_and_hours_list_the_choices(client):
    response = client.post("/recommend", json={**GALLE_BODY, "skills": ["juggling"], "hours": "lots"})
    assert response.status_code == 422
    skills_message, hours_message = messages(response)
    assert skills_message.startswith("skills must be one of:") and "sewing" in skills_message
    assert hours_message.startswith("hours must be one of:") and "10-20" in hours_message


def test_missing_field_is_readable(client):
    body = {k: v for k, v in GALLE_BODY.items() if k != "hours"}
    assert messages(client.post("/recommend", json=body)) == ["hours is required"]


def test_official_district_without_data_is_422(client):
    response = client.post("/recommend", json={**GALLE_BODY, "district": "Colombo"})
    assert response.status_code == 422
    assert "Colombo" in messages(response)[0]


def test_gaps_ranks_adequate_and_lists_the_rest_as_not_ranked(client):
    body = client.get("/gaps", params={"category_id": "tailoring_clothing"}).json()
    assert [row["district"] for row in body["ranked"]] == ["Galle", "Badulla"]
    assert body["ranked"][0]["gap_score"] >= body["ranked"][1]["gap_score"]
    assert {(r["district"], r["status"], r["coverage_flag"]) for r in body["not_ranked"]} == {
        ("Monaragala", "not ranked", "insufficient"),
        ("Kalutara", "not ranked", "low"),
    }


def test_gaps_unknown_category_is_422(client):
    response = client.get("/gaps", params={"category_id": "nope"})
    assert response.status_code == 422
    assert messages(response)[0].startswith("category_id must be one of:")


def test_gaps_requires_category_id(client):
    assert messages(client.get("/gaps")) == ["category_id is required"]


def test_gaps_ranks_nothing_when_data_is_too_stale():
    old = {**FRESH_SOURCES, "osm": {"snapshot_date": "2026-08-01"}, "prices": {"last_date": "2026-08-01"}}
    with client_for(old) as client:
        body = client.get("/gaps", params={"category_id": "tailoring_clothing"}).json()
    assert body["ranked"] == []
    assert len(body["not_ranked"]) == 4


def test_cors_allows_dev_origin(client):
    response = client.get("/health", headers={"Origin": config.DEV_FRONTEND_ORIGIN})
    assert response.headers["access-control-allow-origin"] == config.DEV_FRONTEND_ORIGIN


def test_cors_blocks_other_origins(client):
    response = client.get("/health", headers={"Origin": "https://example.com"})
    assert "access-control-allow-origin" not in response.headers


def test_cors_reads_production_origin_from_env(monkeypatch):
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://lens.example.com")
    with client_for() as client:
        response = client.get("/health", headers={"Origin": "https://lens.example.com"})
    assert response.headers["access-control-allow-origin"] == "https://lens.example.com"


def test_committed_data_answers_every_district():
    """End to end on the committed data files, so every official district gets a real answer."""
    from datetime import date, timedelta

    from app.data_loader import load_all

    data = load_all()
    today = date.fromisoformat(data.sources["prices"]["last_date"]) + timedelta(days=1)
    with TestClient(create_app(load_store=lambda: data, today=lambda: today)) as client:
        assert len(client.get("/districts").json()) == len(config.DISTRICTS)
        assert len(client.get("/categories").json()) == len(data.categories)
        assert client.get("/gaps", params={"category_id": "tailoring_clothing"}).status_code == 200
        for district in config.DISTRICTS:
            response = client.post("/recommend", json={**GALLE_BODY, "district": district})
            assert response.status_code == 200, district
            body = response.json()
            assert body["status"] in ("ok", "insufficient_data")
            if body["status"] == "ok":
                assert body["disclaimer"] == config.DISCLAIMER
