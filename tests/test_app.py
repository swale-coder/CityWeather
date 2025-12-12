import json
import pytest
from unittest.mock import patch
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
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
        {"dt": 1700000000, "main": {"temp": 26, "humidity": 55}, "weather": [{"description": "clear sky", "main": "Clear"}]},
        {"dt": 1700086400, "main": {"temp": 27, "humidity": 50}, "weather": [{"description": "clouds", "main": "Clouds"}]},
    ]
}

mock_aqi_data = {"list": [{"main": {"aqi": 2}}]}

# -------------------------
# Test index route
# -------------------------
def test_index(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Weather Forecast" in response.data

# -------------------------
# Test /weather route success
# -------------------------
@patch("app.requests.get")
def test_weather_success(mock_get, client):
    # Mock different API endpoints
    def side_effect(url, params):
        if "weather" in url and "forecast" not in url and "air_pollution" not in url:
            return MockResponse(mock_current_data)
        elif "forecast" in url:
            return MockResponse(mock_forecast_data)
        elif "air_pollution" in url:
            return MockResponse(mock_aqi_data)
        return MockResponse({"cod": 404, "message": "Not Found"}, 404)
    
    mock_get.side_effect = side_effect

    response = client.post("/weather", json={"city": "TestCity"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["current"]["name"] == "TestCity"
    assert len(data["forecast"]) > 0
    assert data["current"]["aqi"] == 2

# -------------------------
# Test /weather route missing city
# -------------------------
def test_weather_missing_city(client):
    response = client.post("/weather", json={})
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data

# -------------------------
# Test /weather route city not found
# -------------------------
@patch("app.requests.get")
def test_weather_city_not_found(mock_get, client):
    mock_get.return_value = MockResponse({"cod": 404, "message": "city not found"}, 404)
    response = client.post("/weather", json={"city": "UnknownCity"})
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data

# -------------------------
# Test /weather unexpected error
# -------------------------
@patch("app.requests.get", side_effect=Exception("API fail"))
def test_weather_exception(mock_get, client):
    response = client.post("/weather", json={"city": "TestCity"})
    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data

# -------------------------
# Helper class to mock requests
# -------------------------
class MockResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code
    def json(self):
        return self._json
