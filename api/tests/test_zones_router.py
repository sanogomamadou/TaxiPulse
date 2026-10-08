def test_list_zones_returns_empty_before_anything_is_ingested(client):
    response = client.get("/zones")

    assert response.status_code == 200
    assert response.json() == []


def test_list_zones_returns_seeded_zones(client, seeded_warehouse):
    response = client.get("/zones")

    assert response.status_code == 200
    body = response.json()
    assert [z["location_id"] for z in body] == [100, 200, 264]
    assert body[0]["zone_name"] == "Midtown"


def test_list_zones_serializes_nan_fields_as_null(client, seeded_warehouse):
    """Real TLC zone data has placeholder zones with missing string
    fields, stored by pandas as float NaN rather than None - this must
    come back as JSON null, not fail response validation."""
    response = client.get("/zones")

    assert response.status_code == 200
    placeholder = next(z for z in response.json() if z["location_id"] == 264)
    assert placeholder["zone_name"] is None
    assert placeholder["service_zone"] is None
    assert placeholder["centroid_lat"] is None


def test_get_zone_by_id(client, seeded_warehouse):
    response = client.get("/zones/100")

    assert response.status_code == 200
    assert response.json()["borough"] == "Manhattan"


def test_get_zone_404_for_unknown_id(client, seeded_warehouse):
    response = client.get("/zones/999")

    assert response.status_code == 404


def test_get_zone_demand_sorted_most_recent_first(client, seeded_warehouse):
    response = client.get("/zones/100/demand?bucket=hourly")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["period_start"] > body[1]["period_start"]
    assert body[0]["trip_count"] == 30


def test_get_zone_demand_respects_limit(client, seeded_warehouse):
    response = client.get("/zones/100/demand?bucket=hourly&limit=1")

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_zone_demand_empty_for_zone_with_no_rows(client, seeded_warehouse):
    response = client.get("/zones/999/demand")

    assert response.status_code == 200
    assert response.json() == []


def test_top_zones_by_trip_count(client, seeded_warehouse):
    response = client.get("/zones/top?metric=trip_count&limit=5")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["pickup_location_id"] == 100
    assert body[0]["trip_count"] == 80  # 50 + 30 across both hourly rows


def test_get_zone_forecast(client, seeded_warehouse):
    response = client.get("/zones/100/forecast")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["predicted_trip_count"] == 45.0


def test_get_zone_forecast_empty_for_unforecasted_zone(client, seeded_warehouse):
    response = client.get("/zones/200/forecast")

    assert response.status_code == 200
    assert response.json() == []


def test_latest_spikes_only_returns_flagged_zones(client, seeded_warehouse):
    response = client.get("/zones/spikes")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["pickup_location_id"] == 100
    assert body[0]["is_spike"] is True


def test_latest_spikes_empty_before_pipeline_has_run(client):
    response = client.get("/zones/spikes")

    assert response.status_code == 200
    assert response.json() == []
