from flask import Flask, render_template_string, request, jsonify
import requests
from datetime import datetime
import os

app = Flask(__name__)

# ====================================================
# API KEY HANDLING (CI + PYTEST SAFE)
# ====================================================
API_KEY = os.getenv("API_KEY")

# Pytest automatically sets this env variable
IS_PYTEST = "PYTEST_CURRENT_TEST" in os.environ

if not API_KEY and not IS_PYTEST:
    raise RuntimeError("❌ Missing API_KEY environment variable")

# ====================================================
# API ENDPOINTS
# ====================================================
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
AQI_URL = "https://api.openweathermap.org/data/2.5/air_pollution"

# ====================================================
# HTML TEMPLATE (CLEAN + OPTIMIZED)
# ====================================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Weather App</title>

<style>
body {
    margin: 0;
    padding: 0;
    font-family: Arial, sans-serif;
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
}
.container { max-width: 900px; margin: auto; padding: 20px; }
h1 { text-align: center; }

.search-box {
    background: white; color: black;
    padding: 20px; border-radius: 12px;
    margin-bottom: 20px;
}
input, button {
    width: 100%; padding: 12px;
    margin-top: 8px;
    border-radius: 8px;
    border: none;
}
button { background: #667eea; color: white; cursor: pointer; }
button:hover { opacity: 0.9; }

.box {
    background: white; color: black;
    padding: 20px; border-radius: 12px;
    margin-top: 20px;
    display: none;
}

.forecast-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 10px;
}

.card {
    background: #f1f1ff;
    padding: 10px;
    border-radius: 8px;
    text-align: center;
}
.error { background: #ff4e4e; padding: 10px; border-radius: 8px; display: none; }
.loading { text-align: center; display: none; }
</style>
</head>

<body>
<div class="container">
<h1>🌤 Weather Forecast</h1>

<div class="search-box">
    <input id="city" placeholder="Enter city name">
    <button onclick="fetchWeather()">Search</button>
</div>

<div id="error" class="error"></div>
<div id="loading" class="loading">Loading...</div>

<div id="current" class="box">
    <h2 id="name"></h2>
    <h1 id="temp"></h1>
    <p id="desc"></p>
    <p>Feels Like: <span id="feels"></span></p>
    <p>Humidity: <span id="humidity"></span></p>
    <p>Wind: <span id="wind"></span></p>
    <p>Pressure: <span id="pressure"></span></p>
    <p>AQI: <span id="aqi"></span></p>
</div>

<div id="forecast" class="box">
    <h3>5-Day Forecast</h3>
    <div id="forecastGrid" class="forecast-grid"></div>
</div>
</div>

<script>
async function fetchWeather() {
    const city = document.getElementById("city").value.trim();
    if (!city) return;

    hideAll();
    show("loading");

    try {
        const res = await fetch("/weather", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({city})
        });

        const data = await res.json();
        hide("loading");

        if (!res.ok) {
            showError(data.error);
            return;
        }

        showWeather(data);
    } catch {
        hide("loading");
        showError("Network error");
    }
}

function showWeather(data) {
    const c = data.current;
    document.getElementById("name").textContent = `${c.name}, ${c.country}`;
    document.getElementById("temp").textContent = Math.round(c.temp) + "°C";
    document.getElementById("desc").textContent = c.description;
    document.getElementById("feels").textContent = c.feels_like + "°C";
    document.getElementById("humidity").textContent = c.humidity + "%";
    document.getElementById("wind").textContent = c.wind_speed + " m/s";
    document.getElementById("pressure").textContent = c.pressure + " hPa";
    document.getElementById("aqi").textContent = c.aqi;

    show("current");

    const grid = document.getElementById("forecastGrid");
    grid.innerHTML = "";
    data.forecast.forEach(f => {
        grid.innerHTML += `
            <div class="card">
                <b>${f.date}</b>
                <p>${Math.round(f.temp)}°C</p>
                <p>${f.description}</p>
                <p>${f.humidity}%</p>
            </div>`;
    });
    show("forecast");
}

function hideAll() {
    ["current","forecast","error"].forEach(hide);
}
function show(id){ document.getElementById(id).style.display="block"; }
function hide(id){ document.getElementById(id).style.display="none"; }
function showError(msg){
    const e=document.getElementById("error");
    e.textContent=msg; e.style.display="block";
}
</script>
</body>
</html>
"""

# ====================================================
# ROUTES
# ====================================================
@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/weather", methods=["POST"])
def get_weather():
    try:
        data = request.get_json()
        if not data or not data.get("city"):
            return jsonify({"error": "City name is required"}), 400

        if not API_KEY:
            return jsonify({"error": "API key not configured"}), 500

        city = data["city"].strip()

        current = requests.get(BASE_URL, params={
            "q": city, "appid": API_KEY, "units": "metric"
        }).json()

        if current.get("cod") != 200:
            return jsonify({"error": current.get("message", "City not found")}), 404

        forecast_raw = requests.get(FORECAST_URL, params={
            "q": city, "appid": API_KEY, "units": "metric"
        }).json()

        forecast, used = [], set()
        for item in forecast_raw.get("list", []):
            dt = datetime.fromtimestamp(item["dt"])
            key = dt.strftime("%Y-%m-%d")
            if key not in used and dt.hour >= 12:
                used.add(key)
                forecast.append({
                    "date": dt.strftime("%a, %b %d"),
                    "temp": item.get("main", {}).get("temp", 0),
                    "description": item.get("weather", [{}])[0].get("description", "").title(),
                    "humidity": item.get("main", {}).get("humidity", 0)
                })
                if len(forecast) == 5:
                    break

        aqi_raw = requests.get(AQI_URL, params={
            "lat": current["coord"]["lat"],
            "lon": current["coord"]["lon"],
            "appid": API_KEY
        }).json()

        aqi = aqi_raw.get("list", [{}])[0].get("main", {}).get("aqi", 0)

        return jsonify({
            "current": {
                "name": current["name"],
                "country": current["sys"]["country"],
                "temp": current["main"]["temp"],
                "feels_like": current["main"]["feels_like"],
                "description": current["weather"][0]["description"].title(),
                "humidity": current["main"]["humidity"],
                "wind_speed": current["wind"]["speed"],
                "pressure": current["main"]["pressure"],
                "aqi": aqi
            },
            "forecast": forecast
        })

    except Exception as e:
        return jsonify({"error": f"Unexpected server error: {e}"}), 500

# ====================================================
# RUN
# ====================================================
if __name__ == "__main__":
    app.run(debug=True, port=5000)
