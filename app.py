from flask import Flask, render_template_string, request, jsonify
import requests
from datetime import datetime
import os

app = Flask(__name__)

# ----------------------------------------------------
# API KEY
# ----------------------------------------------------
API_KEY = os.getenv("API_KEY")

if not API_KEY and not os.getenv("PYTEST_RUNNING"):
    raise RuntimeError("❌ Missing API_KEY environment variable")

# ----------------------------------------------------
# API URLs
# ----------------------------------------------------
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
AQI_URL = "https://api.openweathermap.org/data/2.5/air_pollution"

# ----------------------------------------------------
# HTML TEMPLATE
# ----------------------------------------------------
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
h1 { text-align: center; margin-bottom: 20px; }

.search-box {
    background: white; color: black;
    padding: 20px; border-radius: 12px;
    box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    margin-bottom: 25px;
}
#cityInput {
    width: 100%; padding: 12px;
    border-radius: 8px; border: 1px solid #ccc;
    margin-bottom: 10px;
}
button {
    width: 100%; padding: 12px;
    border: none; border-radius: 8px;
    background: #667eea; color: white;
    font-size: 16px; cursor: pointer;
}
button:hover { opacity: 0.9; }

.error, .loading {
    padding: 15px; text-align: center;
    border-radius: 8px; margin-bottom: 15px;
}
.error { background: #ff4e4e; }
.loading { background: #ffffff33; }

.weather-box, .forecast-box {
    background: white; color: black;
    padding: 20px; border-radius: 12px;
    margin-top: 20px;
}
.forecast-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 12px; margin-top: 10px;
}
.forecast-card {
    background: #f1f1ff;
    padding: 15px;
    border-radius: 10px;
    text-align: center;
}
</style>
</head>

<body>
<div class="container">

<h1>🌤 Weather Forecast</h1>

<div class="search-box">
    <input id="cityInput" type="text" placeholder="Enter city name...">
    <button onclick="getWeather()">Search</button>
</div>

<div id="error" class="error" style="display:none"></div>
<div id="loading" class="loading" style="display:none">Loading...</div>

<div id="weatherBox" class="weather-box" style="display:none">
    <h2 id="cityName"></h2>
    <h1 id="temperature"></h1>
    <p id="description"></p>
    <p><b>Feels Like:</b> <span id="feels"></span></p>
    <p><b>Humidity:</b> <span id="humidity"></span></p>
    <p><b>Wind:</b> <span id="wind"></span></p>
    <p><b>Pressure:</b> <span id="pressure"></span></p>
    <p><b>AQI:</b> <span id="aqi"></span></p>
</div>

<div id="forecastBox" class="forecast-box" style="display:none">
    <h3>5-Day Forecast</h3>
    <div id="forecastGrid" class="forecast-grid"></div>
</div>

</div>

<script>
async function getWeather() {
    const city = document.getElementById("cityInput").value.trim();
    if (!city) return;

    hide("weatherBox");
    hide("forecastBox");
    hide("error");
    show("loading");

    try {
        const res = await fetch("/weather", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ city })
        });

        const data = await res.json();
        hide("loading");

        if (!res.ok) {
            showError(data.error || "City not found");
            return;
        }

        displayWeather(data);

    } catch (e) {
        hide("loading");
        showError("Network error. Try again.");
    }
}

function displayWeather(data) {
    const c = data.current;

    document.getElementById("cityName").textContent = `${c.name}, ${c.country}`;
    document.getElementById("temperature").textContent = Math.round(c.temp) + "°C";
    document.getElementById("description").textContent = c.description;
    document.getElementById("feels").textContent = c.feels_like + "°C";
    document.getElementById("humidity").textContent = c.humidity + "%";
    document.getElementById("wind").textContent = c.wind_speed + " m/s";
    document.getElementById("pressure").textContent = c.pressure + " hPa";
    document.getElementById("aqi").textContent = c.aqi;

    show("weatherBox");

    const grid = document.getElementById("forecastGrid");
    grid.innerHTML = "";
    data.forecast.forEach(f => {
        grid.innerHTML += `
            <div class="forecast-card">
                <h4>${f.date}</h4>
                <p><b>${Math.round(f.temp)}°C</b></p>
                <p>${f.description}</p>
                <p>Humidity: ${f.humidity}%</p>
            </div>`;
    });

    show("forecastBox");
}

function show(id) { document.getElementById(id).style.display = "block"; }
function hide(id) { document.getElementById(id).style.display = "none"; }
function showError(msg) {
    const e = document.getElementById("error");
    e.textContent = msg;
    e.style.display = "block";
}
</script>

</body>
</html>
"""

# ----------------------------------------------------
# BACKEND
# ----------------------------------------------------
@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/weather", methods=["POST"])
def get_weather():
    try:
        req = request.get_json()
        if not req or "city" not in req:
            return jsonify({"error": "City name is required"}), 400

        city = req["city"]

        # ------- CURRENT WEATHER -------
        current = requests.get(BASE_URL, params={
            "q": city,
            "appid": API_KEY,
            "units": "metric"
        }).json()

        if current.get("cod") != 200:
            return jsonify({"error": current.get("message", "City not found")}), 404

        # ------- FORECAST -------
        forecast_raw = requests.get(FORECAST_URL, params={
            "q": city,
            "appid": API_KEY,
            "units": "metric"
        }).json()

        daily = []
        used = set()

        for item in forecast_raw.get("list", []):
            dt = datetime.fromtimestamp(item["dt"])
            date_key = dt.strftime("%Y-%m-%d")

            if date_key not in used and dt.hour >= 12:
                used.add(date_key)
                daily.append({
                    "date": dt.strftime("%a, %b %d"),
                    "temp": item["main"]["temp"],
                    "description": item["weather"][0]["description"].title(),
                    "humidity": item["main"]["humidity"]
                })

                if len(daily) == 5:
                    break

        # ------- AQI -------
        lat = current["coord"]["lat"]
        lon = current["coord"]["lon"]

        aqi_raw = requests.get(AQI_URL, params={
            "lat": lat,
            "lon": lon,
            "appid": API_KEY
        }).json()

        aqi_value = aqi_raw["list"][0]["main"]["aqi"]

        # ------- FINAL RESPONSE -------
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
                "aqi": aqi_value
            },
            "forecast": daily
        })

    except Exception as e:
        return jsonify({"error": f"Unexpected server error: {e}"}), 500


# ----------------------------------------------------
# RUN APP
# ----------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, port=5000)
