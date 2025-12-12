import json
import pytest
from unittest.mock import patch
from app import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

# -------------------------
# Mock responses
# -------------------------
mock_current_data = {
    "cod": 200,
    "name": "TestCity",
    "sys": {"country": "TC"},
    "main": {"temp": 25, "feels_like": 24, "humidity": 60, "pressure": 1012},
    "weather": [{"description": "clear sky", "main": "Clear"}],
    "wind": {"speed": 5},
    "coord": {"lat": 10, "lon": 20}
}

mock_forecast_data = {
    "list": [
        {
            "dt": 1700000000,
            "main": {"temp": 26, "humidity": 55},
            "weather": [{"description": "clear sky", "main": "Clear"}],
        },
        {
            "dt": 1700086400,
            "main": {"temp": 27, "humidity": 50},
            "weather": [{"description": "clouds", "main": "Clouds"}],
        },
    ]
}

mock_aqi_data = {"list": [{"main": {"aqi": 2}}]}

# -------------------------
# Helper class to mock requests
# -------------------------
class MockResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        return self._json

# -------------------------
# Index route
# -------------------------
def test_index(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Weather Forecast" in response.data

# -------------------------
# Weather route success
# -------------------------
@patch("app.requests.get")
def test_weather_success(mock_get, client):
    def side_effect(url, params):
        if "weather" in url and "forecast" not in url and "air_pollution" not in url:
            return MockResponse(mock_current_data)
        elif "forecast" in url:
            return MockResponse(mock_forecast_data)
        elif "air_pollution" in url:
            return MockResponse(mock_aqi_data)
        return MockResponse({"cod": 404}, 404)

    mock_get.side_effect = side_effect
    response = client.post("/weather", json={"city": "TestCity"})

    assert response.status_code == 200
    data = response.get_json()

    for key in ["name", "country", "temp", "feels_like", "description", "main", "humidity", "wind_speed", "pressure", "aqi"]:
        assert key in data["current"]

    for day in data["forecast"]:
        for key in ["date", "temp", "description", "main", "humidity"]:
            assert key in day

# -------------------------
# Missing city
# -------------------------
def test_weather_missing_city(client):
    response = client.post("/weather", json={})
    assert response.status_code == 400
    assert "error" in response.get_json()

# -------------------------
# City not found
# -------------------------
@patch("app.requests.get")
def test_weather_city_not_found(mock_get, client):
    mock_get.return_value = MockResponse({"cod": 404, "message": "city not found"}, 404)
    response = client.post("/weather", json={"city": "Unknown"})
    assert response.status_code == 404
    assert "error" in response.get_json()

# -------------------------
# Exception / crash
# -------------------------
@patch("app.requests.get", side_effect=Exception("API fail"))
def test_weather_exception(mock_get, client):
    response = client.post("/weather", json={"city": "TestCity"})
    assert response.status_code == 500
    assert "error" in response.get_json()

# -------------------------
# Special characters
# -------------------------
@patch("app.requests.get")
def test_weather_special_char_city(mock_get, client):
    mock_get.side_effect = [
        MockResponse(mock_current_data),
        MockResponse(mock_forecast_data),
        MockResponse(mock_aqi_data),
        MockResponse(mock_current_data),
        MockResponse(mock_forecast_data),
        MockResponse(mock_aqi_data),
    ]

    response = client.post("/weather", json={"city": "New York"})
    assert response.status_code == 200
    assert response.get_json()["current"]["aqi"] == 2

    response = client.post("/weather", json={"city": "São Paulo"})
    assert response.status_code == 200
    assert response.get_json()["current"]["aqi"] == 2

# ==========================================================
# EXTRA TEST CASES TO BOOST COVERAGE ABOVE 80%
# ==========================================================

# Trim spaces
@patch("app.requests.get")
def test_weather_city_trim(mock_get, client):
    mock_get.side_effect = [
        MockResponse(mock_current_data),
        MockResponse(mock_forecast_data),
        MockResponse(mock_aqi_data),
    ]
    response = client.post("/weather", json={"city": "   TestCity   "})
    assert response.status_code == 200

# Invalid content type
def test_weather_invalid_content_type(client):
    response = client.post("/weather", data="city=TestCity")
    assert response.status_code == 400

# Rate limit
@patch("app.requests.get")
def test_weather_rate_limit(mock_get, client):
    mock_get.return_value = MockResponse({"cod": 429}, 429)
    response = client.post("/weather", json={"city": "TestCity"})
    assert "error" in response.get_json()

# Timeout
@patch("app.requests.get", side_effect=pytest.TimeoutError)
def test_weather_timeout(mock_get, client):
    response = client.post("/weather", json={"city": "TestCity"})
    assert response.status_code == 500

# None API response
@patch("app.requests.get")
def test_weather_api_none(mock_get, client):
    mock_get.return_value = None
    response = client.post("/weather", json={"city": "TestCity"})
    assert response.status_code == 500

# Missing weather details
@patch("app.requests.get")
def test_weather_missing_description(mock_get, client):
    broken = dict(mock_current_data)
    broken["weather"] = []
    mock_get.side_effect = [
        MockResponse(broken),
        MockResponse(mock_forecast_data),
        MockResponse(mock_aqi_data),
    ]
    response = client.post("/weather", json={"city": "TestCity"})
    assert response.status_code == 200

# Empty AQI list
@patch("app.requests.get")
def test_weather_aqi_empty(mock_get, client):
    mock_get.side_effect = [
        MockResponse(mock_current_data),
        MockResponse(mock_forecast_data),
        MockResponse({"list": []}),
    ]
    response = client.post("/weather", json={"city": "TestCity"})
    assert response.status_code == 200

# Forecast missing temperature
@patch("app.requests.get")
def test_weather_forecast_missing_temp(mock_get, client):
    broken = {"list": [{"dt": 1, "main": {}, "weather": [{"description": "", "main": ""}]}]}
    mock_get.side_effect = [
        MockResponse(mock_current_data),
        MockResponse(broken),
        MockResponse(mock_aqi_data),
    ]
    response = client.post("/weather", json={"city": "TestCity"})
    assert response.status_code == 200

# Large forecast list
@patch("app.requests.get")
def test_weather_large_forecast(mock_get, client):
    big = {
        "list": [{
            "dt": 1700000000 + i,
            "main": {"temp": (i % 30), "humidity": 50},
            "weather": [{"description": "clear", "main": "Clear"}],
        } for i in range(150)]
    }
    mock_get.side_effect = [
        MockResponse(mock_current_data),
        MockResponse(big),
        MockResponse(mock_aqi_data),
    ]
    response = client.post("/weather", json={"city": "MegaCity"})
    assert response.status_code == 200

# Unicode city
@patch("app.requests.get")
def test_weather_unicode_city(mock_get, client):
    mock_get.side_effect = [
        MockResponse(mock_current_data),
        MockResponse(mock_forecast_data),
        MockResponse(mock_aqi_data),
    ]
    response = client.post("/weather", json={"city": "અમદાવાદ"})
    assert response.status_code == 200
