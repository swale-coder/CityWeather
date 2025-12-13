# tests/test_app.py
import os
import pytest
from unittest.mock import patch
from app import app  # import your Flask app

# ====================================================
# Ensure testing mode
# ====================================================
os.environ["PYTEST_CURRENT_TEST"] = "1"

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

# ====================================================
# Mock API responses
# ====================================================
mock_current_data = {
    "name": "TestCity",
    "sys": {"country": "TC"},
    "main": {"temp": 25, "feels_like": 24, "humidity": 50, "pressure": 1013},
    "weather": [{"description": "clear sky", "main": "Clear"}],
    "wind": {"speed": 5},
    "coord": {"lat": 10, "lon": 20},
    "cod": 200
}

mock_forecast_data = {
    "list": [
        {"dt": 1700000000 + i*86400,
         "main": {"temp": 20 + i, "humidity": 50 + i},
         "weather": [{"description": "sunny", "main": "Clear"}]}
        for i in range(5)
    ]
}

mock_aqi_data = {"list": [{"main": {"aqi": 1}}]}

# Helper class to mock requests responses
class MockResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        return self._json

# ====================================================
# TEST CASES
# ====================================================

@patch("app.requests.get")
def test_weather_success(mock_get, client):
    """Test successful weather request"""
    mock_get.side_effect = [
        MockResponse(mock_current_data),
        MockResponse(mock_forecast_data),
        MockResponse(mock_aqi_data),
    ]
    response = client.post("/weather", json={"city": "TestCity"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["current"]["name"] == "TestCity"
    assert len(data["forecast"]) == 5
    assert data["current"]["aqi"] == 1

def test_weather_empty_city(client):
    """Test empty city string"""
    response = client.post("/weather", json={"city": "   "})
    assert response.status_code == 400
    data = response.get_json()
    assert "City" in data["error"]

@patch("app.requests.get")
def test_weather_city_not_found(mock_get, client):
    """Test city not found"""
    mock_get.return_value = MockResponse({"cod": 404, "message": "city not found"})
    response = client.post("/weather", json={"city": "UnknownCity"})
    assert response.status_code == 404
    data = response.get_json()
    assert "not found" in data["error"].lower()

@patch("app.requests.get")
def test_forecast_less_than_5_days(mock_get, client):
    """Test forecast returns less than 5 days"""
    short_forecast = {"list": mock_forecast_data["list"][:2]}
    mock_get.side_effect = [
        MockResponse(mock_current_data),
        MockResponse(short_forecast),
        MockResponse(mock_aqi_data),
    ]
    response = client.post("/weather", json={"city": "TestCity"})
    data = response.get_json()
    assert len(data["forecast"]) == 2

@patch("app.requests.get")
def test_aqi_missing(mock_get, client):
    """Test missing AQI data"""
    mock_get.side_effect = [
        MockResponse(mock_current_data),
        MockResponse(mock_forecast_data),
        MockResponse({"list": []}),  # no AQI
    ]
    response = client.post("/weather", json={"city": "TestCity"})
    data = response.get_json()
    assert data["current"]["aqi"] == 0

@patch("app.requests.get")
def test_weather_special_char_city(mock_get, client):
    """Test city with special characters / unicode"""
    mock_get.side_effect = [
        MockResponse(mock_current_data),
        MockResponse(mock_forecast_data),
        MockResponse(mock_aqi_data),
    ]
    response = client.post("/weather", json={"city": "São Paulo"})
    assert response.status_code == 200

@patch("app.requests.get")
def test_weather_trimmed_city(mock_get, client):
    """Test city with spaces"""
    mock_get.side_effect = [
        MockResponse(mock_current_data),
        MockResponse(mock_forecast_data),
        MockResponse(mock_aqi_data),
    ]
    response = client.post("/weather", json={"city": "   TestCity   "})
    assert response.status_code == 200
