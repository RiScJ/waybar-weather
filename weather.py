#!/usr/bin/env python3

import re
import os
import sys
import subprocess
import json
import urllib.request
import datetime
import math
import random

def decode_icon(code, is_day):
    icons = {
        "sun": "  &#xf185;",
        "moon": "  &#xf186;",
        "cloud": "&#xf0c2;",
        "cloud-bolt": "&#xf76c;",
        "snowflake": "  &#xf2dc;",
        "wind": "&#xf72e;",
        "tornado": "&#xf76f;",
        "temperature-low": "&#xf76b;",
        "temperature-high": "&#xf769;",
        "smog": "&#xf75f;",
        "cloud-sun-rain": "&#xf743;",
        "cloud-sun": "&#xf6c4;",
        "cloud-showers-water": "&#xe4e4;",
        "cloud-showers-heavy": "&#xf740;",
        "cloud-rain": "&#xf73d;",
        "cloud-moon-rain": "&#xf73c;",
        "cloud-moon": " &#xf6c3;",
        "default": "  "
    }
    match code:
        case 200:
            icon_status = "cloud-bolt"
        case 201:
            icon_status = "cloud-bolt"
        case 202:
            icon_status = "cloud-bolt"
        case 210:
            icon_status = "cloud-bolt"
        case 211:
            icon_status = "cloud-bolt"
        case 212:
            icon_status = "cloud-bolt"
        case 221:
            icon_status = "cloud-bolt"
        case 230:
            icon_status = "cloud-bolt"
        case 231:
            icon_status = "cloud-bolt"
        case 232:
            icon_status = "cloud-bolt"
        case 500:
            icon_status = "cloud-sun-rain" if is_day else "cloud-moon-rain"
        case 501:
            icon_status = "cloud-sun-rain" if is_day else "cloud-moon-rain"
        case 502:
            icon_status = "cloud-sun-rain" if is_day else "cloud-moon-rain"
        case 503:
            icon_status = "cloud-sun-rain" if is_day else "cloud-moon-rain"
        case 504:
            icon_status = "cloud-sun-rain" if is_day else "cloud-moon-rain"
        case 511:
            icon_status = "snowflake"
        case 520:
            icon_status = "cloud-rain"
        case 521:
            icon_status = "cloud-rain"
        case 522:
            icon_status = "cloud-showers-heavy"
        case 531:
            icon_status = "cloud-rain"
        case 600:
            icon_status = "snowflake"
        case 601:
            icon_status = "snowflake"
        case 602:
            icon_status = "snowflake"
        case 611:
            icon_status = "snowflake"
        case 612:
            icon_status = "snowflake"
        case 613:
            icon_status = "snowflake"
        case 615:
            icon_status = "snowflake"
        case 616:
            icon_status = "snowflake"
        case 620:
            icon_status = "snowflake"
        case 621:
            icon_status = "snowflake"
        case 622:
            icon_status = "snowflake"
        case 800:
            icon_status = "sun" if is_day else "moon"
        case 801:
            icon_status = "cloud-sun" if is_day else "cloud-moon"
        case 802:
            icon_status = "cloud"
        case 803:
            icon_status = "cloud"
        case 804:
            icon_status = "cloud"
        case 10001:
            icon_status = "temperature-low"
        case 10002:
            icon_status = "temperature-high"
        case _:
            icon_status = "default"
    icon = (
        icons[icon_status]
        if icon_status in icons
        else icons["default"]
    )
    return icon

def is_daytime(dt, resp):
    events = []
    for day in range(8):
        events.append(resp['daily'][day]['sunrise'])
        events.append(resp['daily'][day]['sunset'])
    events.append(dt)
    events.sort()
    return events.index(dt) % 2 == 1

def format_temp(temp):
    rounded_temp = round(temp)
    return f"{rounded_temp: >3}°"

def render_minutely_precip_chart(resp):
    chart = ""
    icons = [" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
    for minute in range(60):
        precip = resp['minutely'][minute]['precipitation']
        precip = math.ceil(precip)
        precip = 8 if precip > 8 else precip
#        precip = random.randint(0, 8)
        chart = chart + icons[precip]
    return chart

def format_precip_chart_string(chart, resp):
    total_precip = 0
    for minute in range(60):
        total_precip = total_precip + resp['minutely'][minute]['precipitation']
#    total_precip = 1
    if total_precip == 0:
        return ""
    else:
        first_minute = resp['minutely'][minute]['dt']
        first_minute = datetime.datetime.fromtimestamp(first_minute).minute
        
        seq = ["15", "30", "45", " 0"]

        first_target = seq[int(first_minute / 15)]
        init_spaces = int(first_target) - first_minute
        timelabel = " "
        for i in range(init_spaces):
            timelabel = timelabel + " "
        for i in range(4):
            timelabel = timelabel + seq[(int(first_minute / 15) + i) % 4]
            if i < 3:
                timelabel = timelabel + "             "

        chart_string = f"<span font_family=\"Fantasque Sans Mono\">  {chart}  </span>\n"
        chart_string = chart_string + f"<span font_family=\"Fantasque Sans Mono\">{timelabel}</span>\n\n"
        return chart_string

def get_hourly_hours(hours, resp):
    hour_string = ""
    for hour in range(hours):
        dt = resp['hourly'][hour]['dt']
        dt = datetime.datetime.fromtimestamp(dt).hour
        hour_string = hour_string + " " + f"{dt:2}" + " "
    return hour_string

def get_hourly_icons(hours, resp):
    icon_string = ""
    for hour in range(hours):
        status_code = resp['hourly'][hour]['weather'][0]['id']
        dt = resp['hourly'][hour]['dt']
        hour_is_daytime = is_daytime(dt, resp)
        icon_string = icon_string + " " + decode_icon(status_code, hour_is_daytime) + " "
    return icon_string

def get_hourly_temps(hours, resp):
    temp_string = ""
    for hour in range(hours):
        temp_string = temp_string + format_temp(resp['hourly'][hour]['temp'])
    return temp_string

def compute_daily_minmax(days, resp):
    dmin = 100
    dmax = -100
    for day in range(days):
        day_min = resp['daily'][day]['temp']['min']
        day_max = resp['daily'][day]['temp']['max']
        if day_min < dmin: dmin = day_min
        if day_max > dmax: dmax = day_max
    return dmin, dmax

def format_percentage(num):
    num = str(int(100 * num))
    for i in range(3 - len(num)):
        num = " " + num
    num = num + "%"
    return num

def get_daily(days, resp, dlow, dhigh):
    delta = dhigh - dlow
    steps = 20
    incr = delta / steps

    if days == 0:
        return ""
    daily_string = "\n"
    for day in range(days):
        dt = resp['daily'][day]['dt']
        dt = datetime.datetime.fromtimestamp(dt)
        dt = dt.strftime('%a %b %e')
        code = resp['daily'][day]['weather'][0]['id']
        icon = decode_icon(code, True)
        day_min = resp['daily'][day]['temp']['min']
        day_max = resp['daily'][day]['temp']['max']
        lt = format_temp(day_min)
        ht = format_temp(day_max)
        pop = format_percentage(resp['daily'][day]['pop'])
        daily_string = daily_string + "\n<span font_family=\"Fantasque Sans Mono\" size=\"large\">" + dt \
            + "  " + icon + "  " + pop + " " + lt + " "
        day_tempc_startc = int((day_min - dlow) / incr)
        day_tempc_stopc = int((day_max - dlow) / incr)

        for character in range(steps):
            if character < day_tempc_startc:
                daily_string = daily_string + " "
            elif character > day_tempc_stopc:
                daily_string = daily_string + " "
            else:
                daily_string = daily_string + "─"            
        
        daily_string = daily_string + ht + "</span>"
    return daily_string

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
    valid_units = ['metric', 'standard', 'imperial']
    return units.lower() in valid_units

URL = "https://api.openweathermap.org/data/3.0/onecall?"

try:
    config_file = os.path.expanduser("~/.config/waybar/weather.conf")
    with open(config_file, "r") as file:
        for line in file:
            key, value = line.strip().replace(" ", "").split("=")
            if key == "lat":
                if not validate_latitude(value):
                    print("Error: Invalid latitude")
                    sys.exit(1)
            elif key == "lon":
                if not validate_longitude(value):
                    print("Error: Invalid longitude")
                    sys.exit(1)
            elif key == "units":
                if not validate_units(value):
                    print("Error: Invalid units")
                    sys.exit(1)
            elif key == "appid":
                pass
            else:
                print("Error: Unknown key '{}'".format(key))
                sys.exit(1)
            URL = URL + "&" + key + "=" + value
except FileNotFoundError:
    print("Error: File '{}' not found".format(config_file))
    sys.exit(1)

with urllib.request.urlopen(URL) as url:
    resp = json.load(url)

current_status_code = resp['current']['weather'][0]['id']
current_temp = round(resp['current']['temp'])
current_desc = resp['current']['weather'][0]['description']
current_dt = resp['current']['dt']
current_is_daytime = is_daytime(current_dt, resp)
current_icon = decode_icon(current_status_code, current_is_daytime)

precipitation_chart = render_minutely_precip_chart(resp)
precip_chart_string = format_precip_chart_string(precipitation_chart, resp)

hours_to_show = 16
hourly_hours = get_hourly_hours(hours_to_show, resp)
hourly_icons = get_hourly_icons(hours_to_show, resp)
hourly_temps = get_hourly_temps(hours_to_show, resp)

days_to_show = 8
dlow, dhigh = compute_daily_minmax(days_to_show, resp)
daily_forecast = get_daily(days_to_show, resp, dlow, dhigh)

tooltip_text = f"<span font_family=\"Fantasque Sans Mono\" size=\"xx-large\">{current_icon} {current_desc}</span>\n\n" \
    + precip_chart_string \
    + f"<span font_family=\"Fantasque Sans Mono\">{hourly_hours}</span>\n" \
    + f"<span font_family=\"Fantasque Sans Mono\">{hourly_icons}</span>\n" \
    + f"<span font_family=\"Fantasque Sans Mono\">{hourly_temps}</span>" \
    + daily_forecast

out_data = {
    "text": f"{current_icon} {current_temp} °C",
    "class": current_status_code,
    "alt": current_desc,
    "tooltip": tooltip_text
}

print(json.dumps(out_data))
