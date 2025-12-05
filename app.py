from flask import Flask, render_template_string, request, jsonify
import requests
from datetime import datetime

app = Flask(__name__)

API_KEY = "fbe36394e522d7ee060e8774229a074c"
BASE_URL = "http://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "http://api.openweathermap.org/data/2.5/forecast"
AQI_URL = "http://api.openweathermap.org/data/2.5/air_pollution"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Weather Forecast App</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
       background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
       min-height: 100vh; padding: 20px; color: #333; }
.container { max-width: 1200px; margin: 0 auto; }
header { text-align: center; color: white; margin-bottom: 30px; }
h1 { font-size: 2.5em; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.2); }
.search-box { background: white; padding: 30px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); margin-bottom: 30px; }
.search-form { display: flex; gap: 10px; }
#cityInput { flex: 1; padding: 15px 20px; font-size: 16px; border: 2px solid #e0e0e0; border-radius: 10px; outline: none; transition: border-color 0.3s; }
#cityInput:focus { border-color: #667eea; }
button { padding: 15px 30px; font-size: 16px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 10px; cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; font-weight: 600; }
button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.2); }
button:active { transform: translateY(0); }
.weather-display { display: grid; grid-template-columns: 1fr; gap: 20px; }
.current-weather, .forecast-section { background: white; padding: 30px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
.current-weather { text-align: center; }
.weather-icon { font-size: 80px; margin: 20px 0; }
.temperature { font-size: 4em; font-weight: bold; color: #667eea; }
.description { font-size: 1.5em; color: #666; text-transform: capitalize; margin: 10px 0; }
.city-name { font-size: 2em; margin-bottom: 10px; color: #333; }
.weather-details { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 20px; margin-top: 30px; }
.detail-item { background: #f8f9fa; padding: 15px; border-radius: 10px; text-align: center; }
.detail-label { color: #666; font-size: 0.9em; margin-bottom: 5px; }
.detail-value { font-size: 1.3em; font-weight: bold; color: #333; }
.forecast-section h2 { margin-bottom: 20px; color: #333; }
.forecast-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
.forecast-card { background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%); padding: 20px; border-radius: 15px; text-align: center; transition: transform 0.2s; }
.forecast-card:hover { transform: translateY(-5px); }
.forecast-date { font-weight: bold; color: #667eea; margin-bottom: 10px; }
.forecast-icon { font-size: 40px; margin: 10px 0; }
.forecast-temp { font-size: 1.5em; font-weight: bold; margin: 10px 0; }
.error-message { background: #ff4444; color: white; padding: 15px; border-radius: 10px; margin-bottom: 20px; text-align: center; }
.loading { text-align: center; padding: 40px; font-size: 1.2em; color: #667eea; }
.hidden { display: none; }
@media (max-width: 768px) { h1 { font-size: 2em; } .search-form { flex-direction: column; } .temperature { font-size: 3em; } }
</style>
</head>
<body>
<div class="container">
<header>
    <h1>🌤️ Weather Forecast</h1>
    <p>Get current weather, AQI, and 5-day forecast for any city</p>
</header>

<div class="search-box">
    <form class="search-form" id="searchForm">
        <input type="text" id="cityInput" placeholder="Enter city name" required>
        <button type="submit">Search</button>
    </form>
</div>

<div id="errorMessage" class="error-message hidden"></div>
<div id="loading" class="loading hidden">Loading weather data...</div>

<div id="weatherDisplay" class="weather-display hidden">
    <div class="current-weather">
        <div class="city-name" id="cityName"></div>
        <div class="weather-icon" id="weatherIcon"></div>
        <div class="temperature" id="temperature"></div>
        <div class="description" id="description"></div>
        <div class="weather-details">
            <div class="detail-item">
                <div class="detail-label">Feels Like</div>
                <div class="detail-value" id="feelsLike"></div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Humidity</div>
                <div class="detail-value" id="humidity"></div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Wind Speed</div>
                <div class="detail-value" id="windSpeed"></div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Pressure</div>
                <div class="detail-value" id="pressure"></div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Air Quality Index</div>
                <div class="detail-value" id="aqi"></div>
            </div>
        </div>
    </div>

    <div class="forecast-section">
        <h2>5-Day Forecast</h2>
        <div class="forecast-grid" id="forecastGrid"></div>
    </div>
</div>
</div>

<script>
const weatherIcons = {
    'Clear': '☀️', 'Clouds': '☁️', 'Rain': '🌧️', 'Drizzle': '🌦️', 'Thunderstorm': '⛈️',
    'Snow': '❄️', 'Mist': '🌫️', 'Smoke': '💨', 'Haze': '🌫️', 'Dust': '💨',
    'Fog': '🌫️', 'Sand': '💨', 'Ash': '🌋', 'Squall': '💨', 'Tornado': '🌪️'
};
const aqiLabels = ['Good', 'Fair', 'Moderate', 'Poor', 'Very Poor'];
const aqiColors = ['#00e400', '#9cff00', '#ffff00', '#ff7e00', '#ff0000'];

const searchForm = document.getElementById('searchForm');
const cityInput = document.getElementById('cityInput');
const errorMessage = document.getElementById('errorMessage');
const loadingEl = document.getElementById('loading');
const weatherDisplay = document.getElementById('weatherDisplay');

searchForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const city = cityInput.value.trim();
    if (!city) return;

    showLoading();
    hideError();
    hideWeather();

    try {
        const response = await fetch('/weather', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ city })
        });

        if (!response.ok) {
            const errData = await response.json();
            showError(errData.error || 'City not found');
            return;
        }

        const data = await response.json();
        displayWeather(data);

    } catch (error) {
        showError('Failed to fetch weather data. Check your internet.');
    } finally {
        hideLoading();
    }
});

function displayWeather(data) {
    document.getElementById('cityName').textContent = `${data.current.name}, ${data.current.country}`;
    document.getElementById('weatherIcon').textContent = weatherIcons[data.current.main] || '🌈';
    document.getElementById('temperature').textContent = `${Math.round(data.current.temp)}°C`;
    document.getElementById('description').textContent = data.current.description;
    document.getElementById('feelsLike').textContent = `${Math.round(data.current.feels_like)}°C`;
    document.getElementById('humidity').textContent = `${data.current.humidity}%`;
    document.getElementById('windSpeed').textContent = `${data.current.wind_speed} m/s`;
    document.getElementById('pressure').textContent = `${data.current.pressure} hPa`;
    const aqiIndex = data.current.aqi - 1;
    document.getElementById('aqi').textContent = `${aqiLabels[aqiIndex]} (${data.current.aqi})`;
    document.getElementById('aqi').style.color = aqiColors[aqiIndex];

    const forecastGrid = document.getElementById('forecastGrid');
    forecastGrid.innerHTML = '';
    data.forecast.forEach(day => {
        const card = document.createElement('div');
        card.className = 'forecast-card';
        card.innerHTML = `
            <div class="forecast-date">${day.date}</div>
            <div class="forecast-icon">${weatherIcons[day.main] || '🌈'}</div>
            <div class="forecast-temp">${Math.round(day.temp)}°C</div>
            <div>${day.description}</div>
            <div style="margin-top: 10px; font-size: 0.9em; color: #666;">💧 ${day.humidity}%</div>
        `;
        forecastGrid.appendChild(card);
    });
    showWeather();
}

function showLoading() { loadingEl.classList.remove('hidden'); }
function hideLoading() { loadingEl.classList.add('hidden'); }
function showError(msg) { errorMessage.textContent = msg; errorMessage.classList.remove('hidden'); }
function hideError() { errorMessage.classList.add('hidden'); }
function showWeather() { weatherDisplay.classList.remove('hidden'); }
function hideWeather() { weatherDisplay.classList.add('hidden'); }
</script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/weather', methods=['POST'])
def get_weather():
    try:
        data = request.get_json()
        if not data or not data.get('city'):
            return jsonify({'error': 'City name is required'}), 400
        city = data['city'].strip()

        # Current weather
        current_data = requests.get(BASE_URL, params={'q': city, 'appid': API_KEY, 'units': 'metric'}).json()
        if current_data.get('cod') != 200:
            return jsonify({'error': current_data.get('message', 'City not found')}), 404

        # Forecast
        forecast_data = requests.get(FORECAST_URL, params={'q': city, 'appid': API_KEY, 'units': 'metric'}).json()
        daily_forecast, seen_dates = [], set()
        for item in forecast_data.get('list', []):
            date_obj = datetime.fromtimestamp(item['dt'])
            date_str = date_obj.strftime('%Y-%m-%d')
            if date_str not in seen_dates and date_obj.hour >= 12:
                seen_dates.add(date_str)
                daily_forecast.append({
                    'date': date_obj.strftime('%a, %b %d'),
                    'temp': item['main']['temp'],
                    'description': item['weather'][0]['description'].title(),
                    'main': item['weather'][0]['main'],
                    'humidity': item['main']['humidity']
                })
                if len(daily_forecast) >= 5: break

        # AQI
        lat, lon = current_data['coord']['lat'], current_data['coord']['lon']
        aqi_data = requests.get(AQI_URL, params={'lat': lat, 'lon': lon, 'appid': API_KEY}).json()
        aqi_value = aqi_data['list'][0]['main']['aqi']

        return jsonify({
            'current': {
                'name': current_data['name'],
                'country': current_data['sys']['country'],
                'temp': current_data['main']['temp'],
                'feels_like': current_data['main']['feels_like'],
                'description': current_data['weather'][0]['description'].title(),
                'main': current_data['weather'][0]['main'],
                'humidity': current_data['main']['humidity'],
                'wind_speed': current_data['wind']['speed'],
                'pressure': current_data['main']['pressure'],
                'aqi': aqi_value
            },
            'forecast': daily_forecast
        })

    except Exception as e:
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
