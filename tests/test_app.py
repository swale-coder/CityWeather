from flask import Flask, request, jsonify
import requests
import os
from datetime import datetime

app = Flask(__name__)

API_KEY = os.getenv("API_KEY")

BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
AQI_URL = "https://api.openweathermap.org/data/2.5/air_pollution"


@app.route("/weather", methods=["POST"])
def get_weather():
    try:
        data = request.get_json()

        # -------------------------------
        # Validate request
        # -------------------------------
        if not data or "city" not in data:
            return jsonify({"error": "City name is required"}), 400

        city = data["city"].strip()
        if not city:
            return jsonify({"error": "City name is required"}), 400

        if not API_KEY:
            return jsonify({"error": "API key not configured"}), 500

        # -------------------------------
        # Current weather
        # -------------------------------
        current_resp = requests.get(
            BASE_URL,
            params={"q": city, "appid": API_KEY, "units": "metric"}
        )
        current = current_resp.json()

        if current.get("cod") != 200:
            return jsonify({
                "error": current.get("message", "City not found")
            }), 404

        # -------------------------------
        # Forecast
        # -------------------------------
        forecast_resp = requests.get(
            FORECAST_URL,
            params={"q": city, "appid": API_KEY, "units": "metric"}
        )
        forecast_raw = forecast_resp.json()

        forecast = []
        used_dates = set()

        for item in forecast_raw.get("list", []):
            dt = datetime.fromtimestamp(item["dt"])
            day_key = dt.strftime("%Y-%m-%d")

            if day_key not in used_dates:
                used_dates.add(day_key)
                forecast.append({
                    "date": dt.strftime("%a, %b %d"),
                    "temp": item.get("main", {}).get("temp", 0),
                    "description": item.get("weather", [{}])[0]
                        .get("description", "").title(),
                    "humidity": item.get("main", {}).get("humidity", 0),
                })

            if len(forecast) == 5:
                break

        # -------------------------------
        # AQI (safe handling)
        # -------------------------------
        aqi_resp = requests.get(
            AQI_URL,
            params={
                "lat": current["coord"]["lat"],
                "lon": current["coord"]["lon"],
                "appid": API_KEY
            }
        )
        aqi_raw = aqi_resp.json()

        aqi_list = aqi_raw.get("list", [])
        aqi = aqi_list[0]["main"]["aqi"] if aqi_list else 0

        # -------------------------------
        # Final response
        # -------------------------------
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
        }), 200

    except Exception as e:
        return jsonify({"error": f"Unexpected server error: {e}"}), 500
