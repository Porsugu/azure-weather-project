import os
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
import requests
import azure.functions as func

app = func.FunctionApp() #v2 model

@app.route(route="GetWeather", auth_level=func.AuthLevel.ANONYMOUS) #link  the func to /api/GetWeather
def get_weather(req: func.HttpRequest) -> func.HttpResponse:
    city = req.params.get('city')
    if not city:
        return func.HttpResponse("Please enter city name, Example: ?city=Vancouver", status_code=400)

    api_key = os.environ.get("OPENWEATHER_API_KEY")
    if not api_key:
        return func.HttpResponse("Not set: OPENWEATHER_API_KEY", status_code=500)

    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
    except requests.RequestException as e:
        return func.HttpResponse(f"Check Failed: {e}", status_code=502)

    return func.HttpResponse(r.text, mimetype="application/json")

# organized report
@app.route(route="WeatherReport", auth_level=func.AuthLevel.ANONYMOUS)
def weather_report(req: func.HttpRequest) -> func.HttpResponse:
    city = req.params.get('city')
    days_param = req.params.get('days')  
    days = int(days_param) if days_param and days_param.isdigit() else 3

    if not city:
        return func.HttpResponse("Please enter city name, Example: ?city=Vancouver", status_code=400)

    api_key = os.environ.get("OPENWEATHER_API_KEY")
    if not api_key:
        return func.HttpResponse("Check Failed: OPENWEATHER_API_KEY", status_code=500)

    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
    except requests.RequestException as e:
        return func.HttpResponse(f"Check Failed: {e}", status_code=502)

    # city data and 3 hrs report
    city_info = data.get("city", {})
    tz_offset = city_info.get("timezone", 0)  # sec
    items = data.get("list", [])

    daily = defaultdict(lambda: {
        "min": math.inf, "max": -math.inf,
        "rain_mm": 0.0, "samples": 0,
        "represent": None  
    })

    for it in items:
        # local date
        ts = it.get("dt", 0)
        local_dt = datetime.fromtimestamp(ts + tz_offset, tz=timezone.utc)
        day_key = local_dt.date().isoformat()

        main = it.get("main", {})
        t = main.get("temp")
        if isinstance(t, (int, float)):
            daily[day_key]["min"] = min(daily[day_key]["min"], t)
            daily[day_key]["max"] = max(daily[day_key]["max"], t)

        # Rain vol（mm）：OpenWeather rain.3h
        rain_3h = (it.get("rain") or {}).get("3h", 0.0) or 0.0
        daily[day_key]["rain_mm"] += float(rain_3h)

        # get desciption
        weather_list = it.get("weather") or []
        if weather_list and daily[day_key]["represent"] is None:
            daily[day_key]["represent"] = weather_list[0].get("description", "")

        daily[day_key]["samples"] += 1

    # Get summary for today and n forcast
    sorted_days = sorted(daily.keys())[:days]
    forecast = []
    for d in sorted_days:
        info = daily[d]
        if info["min"] is math.inf:
            continue
        forecast.append({
            "date": d,
            "temp_min_c": round(info["min"], 1),
            "temp_max_c": round(info["max"], 1),
            "rain_mm_sum": round(info["rain_mm"], 1),
            "summary": info["represent"] or ""
        })

    # suggestion
    tips = []
    if forecast:
        if any(day["rain_mm_sum"] >= 5 for day in forecast):
            tips.append("Rain possible, get an umbralla with you")
        if any(day["temp_max_c"] >= 28 for day in forecast):
            tips.append("High temp! 。")
        if any(day["temp_min_c"] <= 0 for day in forecast):
            tips.append("Super cold")
        if not tips:
            tips.append("Good weather, go out!")

    result = {
        "city": {
            "name": city_info.get("name", city),
            "country": city_info.get("country", ""),
        },
        "generated_at_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "horizon_days": days,
        "forecast": forecast,
        "tips": tips
    }

    return func.HttpResponse(json.dumps(result, ensure_ascii=False), mimetype="application/json")