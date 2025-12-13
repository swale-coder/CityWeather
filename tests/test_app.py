import pytest
from app import app
from unittest.mock import patch

# =============================
# Pytest fixture for Flask test client
# =============================
@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

# =============================
# Mock response helper
# =============================
class MockResponse:
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code

    def json(self):
        return self._json_data

# =============================
# Sample mocked data
# =============================
mock_current_data = {
    "name": "TestCity",
    "sys": {"country": "TC"},
    "main": {"temp": 25, "feels_like": 26, "humidity": 50, "pressure": 1010},
    "weather": [{"description": "clear sky", "main": "Clear"}],
    "wind": {"speed": 5},
    "coord": {"lat": 10.0, "lon": 20.0},
    "cod": 200
}

mock_forecast_data = {
    "list": [
        {"dt": 1700000000, "main": {"temp": 25, "humidity": 50}, "weather": [{"description": "clear", "main": "Clear"}]},
        {"dt": 1700086400, "main": {"temp": 27, "humidity": 55}, "weather": [{"description": "cloudy", "main": "Clouds"}]},
        {"dt": 1700172800, "main": {"temp": 28, "humidity": 60}, "weather": [{"description": "rain", "main": "Rain"}]},
        {"dt": 1700259200, "main": {"temp": 24, "humidity": 48}, "weather": [{"description": "sunny", "main": "Clear"}]},
        {"dt": 1700345600, "main": {"temp": 23, "humidity": 52}, "weather": [{"description": "storm", "main": "Storm"}]},
        {"dt": 1700432000, "main": {"temp": 22, "humidity": 50}, "weather": [{"description": "fog", "main": "Fog"}]},
    ]
}

mock_aqi_data = {"list": [{"main": {"aqi": 2}}]}

# =============================
# TEST CASES
# =============================

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
    assert len(data["forecast"]) == 5  # only 5 forecast days returned

@patch("app.requests.get")
def test_weather_city_not_found(mock_get, client):
    """Test city not found"""
    mock_get.return_value = MockResponse({"cod": 404, "message": "city not found"})
    response = client.post("/weather", json={"city": "UnknownCity"})
    assert response.status_code == 404
    assert "city not found" in response.get_json()["error"].lower()

def test_weather_missing_city(client):
    """Test missing city field"""
    response = client.post("/weather", json={})
    assert response.status_code == 400
    assert "required" in response.get_json()["error"].lower()

def test_weather_empty_city(client):
    """Test empty city string"""
    response = client.post("/weather", json={"city": "   "})
    assert response.status_code == 400
    assert "cannot be empty" in response.get_json()["error"].lower()

@patch("app.requests.get")
def test_weather_api_exception(mock_get, client):
    """Test API throws exception"""
    mock_get.side_effect = Exception("API failed")
    response = client.post("/weather", json={"city": "TestCity"})
    assert response.status_code == 500
    assert "unexpected server error" in response.get_json()["error"].lower()

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
    data = response.get_json()
    assert data["current"]["name"] == "TestCity"

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

