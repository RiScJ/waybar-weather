#!/usr/bin/env python3

import os
import sys
import json
import math
import datetime
import urllib.request
import urllib.parse
import urllib.error


WMO_DESCRIPTIONS = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    56: "light freezing drizzle",
    57: "dense freezing drizzle",
    61: "slight rain",
    63: "moderate rain",
    65: "heavy rain",
    66: "light freezing rain",
    67: "heavy freezing rain",
    71: "slight snow fall",
    73: "moderate snow fall",
    75: "heavy snow fall",
    77: "snow grains",
    80: "slight rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    85: "slight snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with slight hail",
    99: "thunderstorm with heavy hail",
}

# JetBrains Nerd Font icons (use for current + hourly)
JBN_ICONS = {
    "sun": "󰖙",
    "moon": "󰖔",
    "cloud": "󰖐",
    "cloud-bolt": "󰖓",
    "snowflake": "󰖘",
    "wind": "󰖝",
    "tornado": "󰼸",
    "temperature-low": "󰔄",
    "temperature-high": "󰔏",
    "smog": "󰖑",
    "cloud-sun-rain": "󰖗",
    "cloud-sun": "󰖕",
    "cloud-showers-water": "󰖖",
    "cloud-showers-heavy": "󰙿",
    "cloud-rain": "󰖖",
    "cloud-moon-rain": "󰼳",
    "cloud-moon": "󰼱",
    "default": "󰖐",
}

# Font Awesome icons (use for daily rows)
FA_ICONS = {
    "sun": "  &#xf185;",
    "moon": "       &#xf186;",
    "cloud": "&#xf0c2;",
    "cloud-bolt": "     &#xf76c;",
    "snowflake": "    &#xf2dc;",
    "wind": "     &#xf72e;",
    "tornado": "       &#xf76f;",
    "temperature-low": "     &#xf76b;",
    "temperature-high": "     &#xf769;",
    "smog": "&#xf75f;",
    "cloud-sun-rain": "&#xf743;",
    "cloud-sun": "&#xf6c4;",
    "cloud-showers-water": "  &#xe4e4;",
    "cloud-showers-heavy": "     &#xf740;",
    "cloud-rain": "  &#xf73d;",
    "cloud-moon-rain": "  &#xf73c;",
    "cloud-moon": "&#xf6c3;",
    "default": "  ",
}

NERD_FONT = "JetBrainsMono Nerd Font Mono"
FA_FONT = "Font Awesome 6 Free Solid"
MONO_FONT = "Fantasque Sans Mono"

HEADER_SIZE = "xx-large"
HOURLY_SIZE = "small"
DAILY_SIZE = "large"


def fail_waybar(text: str, tooltip: str | None = None, class_name: str = "error") -> None:
    print(json.dumps({
        "text": text,
        "class": class_name,
        "alt": text,
        "tooltip": tooltip if tooltip is not None else text,
    }))
    sys.exit(0)


def validate_latitude(lat):
    try:
        lat = float(lat)
        return -90 <= lat <= 90
    except ValueError:
        return False


def validate_longitude(lon):
    try:
        lon = float(lon)
        return -180 <= lon <= 180
    except ValueError:
        return False


def validate_units(units):
    return units.lower() in ["metric", "standard", "imperial"]


def validate_backend(backend):
    return backend.lower() in ["owm", "meteo"]


def load_config():
    config_file = os.path.expanduser("~/.config/waybar/weather.conf")
    cfg = {}
    try:
        with open(config_file, "r", encoding="utf-8") as file:
            for raw_line in file:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    fail_waybar("weather err", f"Invalid config line: {line}")
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if key == "lat":
                    if not validate_latitude(value):
                        fail_waybar("weather err", "Invalid latitude")
                elif key == "lon":
                    if not validate_longitude(value):
                        fail_waybar("weather err", "Invalid longitude")
                elif key == "units":
                    if not validate_units(value):
                        fail_waybar("weather err", "Invalid units")
                elif key == "backend":
                    if not validate_backend(value):
                        fail_waybar("weather err", "Invalid backend")
                elif key == "appid":
                    pass
                else:
                    fail_waybar("weather err", f"Unknown key '{key}'")
                cfg[key] = value
    except FileNotFoundError:
        fail_waybar("weather err", f"File '{config_file}' not found")

    cfg.setdefault("backend", "owm")
    cfg.setdefault("units", "metric")

    if "lat" not in cfg or "lon" not in cfg:
        fail_waybar("weather err", "weather.conf must include lat and lon")
    if cfg["backend"] == "owm" and not cfg.get("appid"):
        fail_waybar("weather err", "backend=owm requires appid")
    return cfg


def http_get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "waybar-weather/nerd-font"})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)


def temp_unit_symbol(units: str) -> str:
    if units == "imperial":
        return "°F"
    if units == "standard":
        return "K"
    return "°C"


def format_temp(temp):
    return f"{round(temp):>2}°"


def format_pop(pop):
    return f"{int(round(pop * 100)):>3}%"


def unix_to_local_dt(ts: int, tz_offset_seconds: int = 0):
    return datetime.datetime.utcfromtimestamp(ts + tz_offset_seconds)


def iso_to_local_dt(iso_s: str):
    return datetime.datetime.fromisoformat(iso_s)


def kelvin_from_c(temp_c):
    return temp_c + 273.15


def classify_icon_status(code: int):
    match int(code):
        case 200 | 201 | 202 | 210 | 211 | 212 | 221 | 230 | 231 | 232:
            return "cloud-bolt"
        case 500 | 501 | 502 | 503 | 504:
            return "cloud-sun-rain"
        case 511:
            return "snowflake"
        case 520 | 521 | 531:
            return "cloud-rain"
        case 522:
            return "cloud-showers-heavy"
        case 600 | 601 | 602 | 611 | 612 | 613 | 615 | 616 | 620 | 621 | 622:
            return "snowflake"
        case 701 | 711 | 721 | 731 | 741 | 751 | 761 | 762:
            return "smog"
        case 771:
            return "wind"
        case 781:
            return "tornado"
        case 800:
            return "sun"
        case 801:
            return "cloud-sun"
        case 802 | 803 | 804:
            return "cloud"
        case 10001:
            return "temperature-low"
        case 10002:
            return "temperature-high"
        case _:
            return "default"


def classify_icon_status_wmo(code: int):
    code = int(code)
    if code == 0:
        return "sun"
    if code == 1:
        return "cloud-sun"
    if code in (2, 3):
        return "cloud"
    if code in (45, 48):
        return "smog"
    if code in (51, 53, 55, 56, 57, 61, 63):
        return "cloud-sun-rain"
    if code in (65, 66, 67, 80, 81, 82):
        return "cloud-rain"
    if code in (71, 73, 75, 77, 85, 86):
        return "snowflake"
    if code in (95, 96, 99):
        return "cloud-bolt"
    return "default"


def apply_day_night_variant(icon_status: str, is_day: bool):
    if icon_status == "sun":
        return "sun" if is_day else "moon"
    if icon_status == "cloud-sun":
        return "cloud-sun" if is_day else "cloud-moon"
    if icon_status == "cloud-sun-rain":
        return "cloud-sun-rain" if is_day else "cloud-moon-rain"
    return icon_status


def decode_icon_owm_jbn(code, is_day):
    icon_status = apply_day_night_variant(classify_icon_status(int(code)), is_day)
    return JBN_ICONS.get(icon_status, JBN_ICONS["default"])


def decode_icon_owm_fa(code, is_day):
    icon_status = apply_day_night_variant(classify_icon_status(int(code)), is_day)
    return FA_ICONS.get(icon_status, FA_ICONS["default"])


def decode_icon_wmo_jbn(code, is_day):
    icon_status = apply_day_night_variant(classify_icon_status_wmo(int(code)), is_day)
    return JBN_ICONS.get(icon_status, JBN_ICONS["default"])


def decode_icon_wmo_fa(code, is_day):
    icon_status = apply_day_night_variant(classify_icon_status_wmo(int(code)), is_day)
    return FA_ICONS.get(icon_status, FA_ICONS["default"])


def build_owm_url(cfg):
    params = {
        "lat": cfg["lat"],
        "lon": cfg["lon"],
        "units": cfg["units"],
        "appid": cfg["appid"],
    }
    return "https://api.openweathermap.org/data/3.0/onecall?" + urllib.parse.urlencode(params)


def build_open_meteo_url(cfg):
    params = {
        "latitude": cfg["lat"],
        "longitude": cfg["lon"],
        "timezone": "auto",
        "forecast_days": "8",
        "current": "temperature_2m,weather_code,is_day",
        "hourly": "temperature_2m,weather_code,is_day,precipitation_probability",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
    }
    if cfg["units"] == "imperial":
        params["temperature_unit"] = "fahrenheit"
        params["precipitation_unit"] = "inch"
        params["wind_speed_unit"] = "mph"
    else:
        params["temperature_unit"] = "celsius"
        params["precipitation_unit"] = "mm"
        params["wind_speed_unit"] = "kmh"
    return "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)


def normalize_alerts_owm(resp):
    alerts_out = []
    for alert in resp.get("alerts", []):
        sender = alert.get("sender_name", "").strip()
        event = alert.get("event", "Alert").strip()
        start_ts = alert.get("start")
        end_ts = alert.get("end")
        description = (alert.get("description") or "").strip()

        time_bits = []
        if start_ts:
            time_bits.append(datetime.datetime.fromtimestamp(start_ts).strftime("%a %H:%M"))
        if end_ts:
            time_bits.append(datetime.datetime.fromtimestamp(end_ts).strftime("%a %H:%M"))

        alerts_out.append({
            "title": f"{sender + ': ' if sender else ''}{event}",
            "time": " → ".join(time_bits),
            "description": description,
        })
    return alerts_out


def normalize_from_owm(resp, units):
    tz_offset = int(resp.get("timezone_offset", 0))

    current_ts = int(resp["current"]["dt"])
    current_code = int(resp["current"]["weather"][0]["id"])
    current_desc = resp["current"]["weather"][0]["description"]

    today = resp["daily"][0]
    sunrise = int(today["sunrise"])
    sunset = int(today["sunset"])
    current_is_day = sunrise <= current_ts < sunset

    current_icon = decode_icon_owm_jbn(current_code, current_is_day)
    current_temp = float(resp["current"]["temp"])

    hourly = []
    for entry in resp.get("hourly", [])[:16]:
        ts = int(entry["dt"])
        dt = unix_to_local_dt(ts, tz_offset)
        code = int(entry["weather"][0]["id"])
        is_day = 6 <= dt.hour < 18
        for day in resp.get("daily", []):
            day_dt = unix_to_local_dt(int(day["dt"]), tz_offset).date()
            if day_dt == dt.date():
                is_day = int(day["sunrise"]) <= ts < int(day["sunset"])
                break
        hourly.append({
            "dt": dt,
            "temp": float(entry["temp"]),
            "icon": decode_icon_owm_jbn(code, is_day),
        })

    daily = []
    for entry in resp.get("daily", [])[:8]:
        dt = unix_to_local_dt(int(entry["dt"]), tz_offset)
        code = int(entry["weather"][0]["id"])
        daily.append({
            "dt": dt,
            "temp_min": float(entry["temp"]["min"]),
            "temp_max": float(entry["temp"]["max"]),
            "pop": float(entry.get("pop", 0.0)),
            "icon": decode_icon_owm_fa(code, True),
        })

    return {
        "backend": "owm",
        "units": units,
        "current_temp": current_temp,
        "current_desc": current_desc,
        "current_icon": current_icon,
        "current_class": str(current_code),
        "hourly": hourly,
        "daily": daily,
        "minutely": resp.get("minutely", []),
        "alerts": normalize_alerts_owm(resp),
    }


def normalize_from_meteo(resp, units):
    current = resp["current"]
    hourly_src = resp["hourly"]
    daily_src = resp["daily"]

    current_temp = float(current["temperature_2m"])
    if units == "standard":
        current_temp = kelvin_from_c(current_temp)

    current_code = int(current["weather_code"])
    current_is_day = bool(int(current.get("is_day", 1)))
    current_desc = WMO_DESCRIPTIONS.get(current_code, "weather")
    current_icon = decode_icon_wmo_jbn(current_code, current_is_day)

    hourly = []
    for i in range(min(16, len(hourly_src["time"]))):
        dt = iso_to_local_dt(hourly_src["time"][i])
        code = int(hourly_src["weather_code"][i])
        temp = float(hourly_src["temperature_2m"][i])
        if units == "standard":
            temp = kelvin_from_c(temp)
        is_day = bool(int(hourly_src.get("is_day", [1] * len(hourly_src["time"]))[i]))
        hourly.append({
            "dt": dt,
            "temp": temp,
            "icon": decode_icon_wmo_jbn(code, is_day),
        })

    daily = []
    for i in range(min(8, len(daily_src["time"]))):
        dt = iso_to_local_dt(daily_src["time"][i])
        code = int(daily_src["weather_code"][i])
        tmin = float(daily_src["temperature_2m_min"][i])
        tmax = float(daily_src["temperature_2m_max"][i])
        if units == "standard":
            tmin = kelvin_from_c(tmin)
            tmax = kelvin_from_c(tmax)
        pop = float(daily_src.get("precipitation_probability_max", [0] * len(daily_src["time"]))[i]) / 100.0
        daily.append({
            "dt": dt,
            "temp_min": tmin,
            "temp_max": tmax,
            "pop": pop,
            "icon": decode_icon_wmo_fa(code, True),
        })

    return {
        "backend": "meteo",
        "units": units,
        "current_temp": current_temp,
        "current_desc": current_desc,
        "current_icon": current_icon,
        "current_class": f"wmo-{current_code}",
        "hourly": hourly,
        "daily": daily,
        "minutely": [],
        "alerts": [],
    }


def fetch_weather(cfg):
    backend = cfg["backend"].lower()
    try:
        if backend == "owm":
            return normalize_from_owm(http_get_json(build_owm_url(cfg)), cfg["units"])
        if backend == "meteo":
            return normalize_from_meteo(http_get_json(build_open_meteo_url(cfg)), cfg["units"])
        fail_waybar("weather err", f"Unsupported backend '{backend}'")
    except urllib.error.HTTPError as e:
        if backend == "owm" and e.code == 401:
            fail_waybar("weather auth", "OpenWeather 401: check appid and One Call access", "auth-error")
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            body = str(e)
        fail_waybar("weather err", f"HTTP {e.code}: {body}", "http-error")
    except urllib.error.URLError as e:
        fail_waybar("weather net", f"Network error: {e}", "network-error")
    except KeyError as e:
        fail_waybar("weather err", f"Unexpected API response. Missing key: {e}", "parse-error")
    except Exception as e:
        fail_waybar("weather err", f"{type(e).__name__}: {e}", "exception")


def span(text, size=DAILY_SIZE, font_family=NERD_FONT):
    return f"<span font_family=\"{font_family}\" size=\"{size}\">{text}</span>"


def hourly_hour_cell(hour):
    tens = str(hour // 10) if hour >= 10 else " "
    ones = str(hour % 10)
    return f" {tens}{ones} "


def hourly_temp_cell(text):
    return f"{text:>4}"


def hourly_icon_cell(icon):
    return f"{icon:>2}"


def render_hourly_hours(hourly):
    return span("".join(hourly_hour_cell(entry["dt"].hour) for entry in hourly[:16]), "10pt")


def render_hourly_icons(hourly):
    return span("".join(hourly_icon_cell(entry["icon"]) for entry in hourly[:16]), "20pt", NERD_FONT)


def render_hourly_temps(hourly):
    return span("".join(hourly_temp_cell(format_temp(entry["temp"])) for entry in hourly[:16]), "10pt")


def compute_daily_minmax(daily):
    dmin = min(day["temp_min"] for day in daily)
    dmax = max(day["temp_max"] for day in daily)
    return dmin, dmax


def render_daily_bar(day_min, day_max, dlow, dhigh, steps=20):
    delta = dhigh - dlow
    incr = delta / steps if delta != 0 else 1
    startc = int((day_min - dlow) / incr)
    stopc = int((day_max - dlow) / incr)
    startc = max(0, min(steps - 1, startc))
    stopc = max(0, min(steps - 1, stopc))
    chars = []
    for idx in range(steps):
        chars.append("─" if startc <= idx <= stopc else " ")
    return "".join(chars)


def big_daily_icon(icon):
    return f"<span font_family=\"{FA_FONT}\" size=\"large\" rise=\"-2pt\">{icon}</span>"


def __align_test__render_daily_rows(daily):
    rows = []

    test_icons = [
        ("sun", FA_ICONS["sun"]),
        ("moon", FA_ICONS["moon"]),
        ("cloud", FA_ICONS["cloud"]),
        ("cloud-bolt", FA_ICONS["cloud-bolt"]),
        ("snowflake", FA_ICONS["snowflake"]),
        ("wind", FA_ICONS["wind"]),
        ("tornado", FA_ICONS["tornado"]),
        ("temperature-low", FA_ICONS["temperature-low"]),
        ("temperature-high", FA_ICONS["temperature-high"]),
        ("smog", FA_ICONS["smog"]),
        ("cloud-sun-rain", FA_ICONS["cloud-sun-rain"]),
        ("cloud-sun", FA_ICONS["cloud-sun"]),
        ("cloud-showers-water", FA_ICONS["cloud-showers-water"]),
        ("cloud-showers-heavy", FA_ICONS["cloud-showers-heavy"]),
        ("cloud-rain", FA_ICONS["cloud-rain"]),
        ("cloud-moon-rain", FA_ICONS["cloud-moon-rain"]),
        ("cloud-moon", FA_ICONS["cloud-moon"]),
    ]

    for name, icon in test_icons:
        rows.append(
            span(
                f"AAA {big_daily_icon(icon)} BBB | {name}",
                "x-large",
                MONO_FONT,
            )
        )

    return "\n".join(rows)


def render_daily_rows(daily):
    dlow, dhigh = compute_daily_minmax(daily)
    rows = []
    for day in daily[:8]:
        dt = day["dt"].strftime("%a %d")
        pop = format_pop(day["pop"])
        lt = format_temp(day["temp_min"])
        ht = format_temp(day["temp_max"])
        bar = render_daily_bar(day["temp_min"], day["temp_max"], dlow, dhigh)
        rows.append(span(f"{dt} {big_daily_icon(day['icon'])} {pop} {lt} {bar} {ht}", "x-large", MONO_FONT))
    return "\n".join(rows)


def render_minutely_precip_chart(minutely):
    if not minutely:
        return ""

    chart = ""
    icons = [" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
    for minute in minutely[:60]:
        precip = math.ceil(float(minute.get("precipitation", 0)))
        precip = 8 if precip > 8 else precip
        chart += icons[precip]

    total_precip = sum(float(minute.get("precipitation", 0)) for minute in minutely[:60])
    if total_precip == 0:
        return ""

    first_ts = int(minutely[0]["dt"])
    first_minute = datetime.datetime.fromtimestamp(first_ts).minute

    seq = ["15", "30", "45", " 0"]
    first_target = seq[int(first_minute / 15)]
    init_spaces = int(first_target) - first_minute

    timelabel = " "
    for _ in range(init_spaces):
        timelabel += " "
    for i in range(4):
        timelabel += seq[(int(first_minute / 15) + i) % 4]
        if i < 3:
            timelabel += "             "

    chart_string = f"<span font_family=\"{MONO_FONT}\">  {chart}  </span>\n"
    chart_string += f"<span font_family=\"{MONO_FONT}\">{timelabel}</span>\n\n"
    return chart_string


def render_alerts(alerts):
    if not alerts:
        return ""

    blocks = []
    for alert in alerts:
        title = alert["title"]
        time_line = alert["time"]
        description = alert["description"]

        block = f"<span font_family=\"{MONO_FONT}\" size=\"10pt\"><b>{title}</b>"
        if time_line:
            block += f"\n{time_line}"
        if description:
            block += f"\n\n{description}"
        block += "</span>"
        blocks.append(block)

    return "\n\n".join(blocks) + "\n\n"


def make_tooltip(data):
    header = span(f"{data['current_icon']} {data['current_desc']}", HEADER_SIZE)
    precip_block = render_minutely_precip_chart(data.get("minutely", [])) if data.get("backend") == "owm" else ""
    alerts_block = render_alerts(data.get("alerts", [])) if data.get("backend") == "owm" else ""
    hourly_block = (
        " " + render_hourly_hours(data["hourly"]) + " "
        + "\n"
        + render_hourly_icons(data["hourly"]) + " "
        + "\n"
        + " " + render_hourly_temps(data["hourly"]) + " "
    )
    daily_block = render_daily_rows(data["daily"])

    parts = [header, ""]
    if precip_block:
        parts.extend([precip_block.rstrip("\n"), ""])
    if alerts_block:
        parts.extend([alerts_block.rstrip("\n"), ""])
    parts.extend([hourly_block, "", daily_block])

    return "\n".join(parts)


def main():
    cfg = load_config()
    data = fetch_weather(cfg)
    unit_symbol = temp_unit_symbol(data["units"])
    out = {
        "text": f"{data['current_icon']} {round(data['current_temp'])} {unit_symbol}",
        "class": data["current_class"],
        "alt": data["current_desc"],
        "tooltip": make_tooltip(data),
    }
    print(json.dumps(out))


if __name__ == "__main__":
    main()
