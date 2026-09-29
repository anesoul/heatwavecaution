import math
import datetime
import requests
from flask import current_app

def dispatch_government_webhook(location_name, lat, lon, current_mri, forecast_times, forecast_mris):

    danger_threshold = current_app.config['THRESHOLD_DANGER']
    extreme_threshold = current_app.config['THRESHOLD_EXTREME']
    
    breach_index = -1
    breach_mri = 0
    hours_until_impact = 0
    
    current_time_str = datetime.datetime.now().strftime("%Y-%m-%dT%H:00")
    current_hour_index = 0
    
    # 1. Scan the 120-hour forecast, completely IGNORING the past
    for idx, time_str in enumerate(forecast_times):

        if time_str == current_time_str:
            current_hour_index = idx
            
        if time_str >= current_time_str:
            mri = forecast_mris[idx]
            
            if mri >= danger_threshold:
                breach_index = idx
                breach_mri = mri

                hours_until_impact = idx - current_hour_index 
                break
                
    if breach_index == -1:
        return False
        
    # 2. Determine Urgency based on TRUE hours from now
    if hours_until_impact <= 24:
        urgency = "Immediate"  # Within the next 24 hours
        action_text = "Deploy emergency ambulances and open public cooling centers immediately."
    else:
        urgency = "Expected"   # 1 to 5 days from now
        action_text = "Activate ward-level medical surge capacity; stage water tankers; alert grid operators."

    # 3. Determine Severity
    severity = "Extreme" if breach_mri >= extreme_threshold else "Severe"

    # 4. Build the NDMA SACHET CAP Standard Payload
    cap_payload = {
        "event": "Extreme Human Thermal Stress",
        "category": "Met/Health",
        "urgency": urgency,
        "severity": severity,
        "certainty": "Likely",
        "areaDesc": location_name,
        "area": {
            "circle": f"{lat},{lon} 3.0"
        },
        "metrics": {
            "projected_mri": breach_mri,
            "time_to_impact_hours": hours_until_impact,
            "onset_time": forecast_times[breach_index]
        },
        "instruction": action_text
    }

    # 6. Check if the affected region is officially subscribed to our API
    from app.routes import registered_webhooks

    target_webhook_url = None
    matched_region = None
    for region, url in registered_webhooks.items():
        if region.lower() in location_name.lower():
            target_webhook_url = url
            matched_region = region
            break

    # 7. Push to Government Server ONLY if they are connected
    if not target_webhook_url:
        print(f"\n[⚠️ ALERT BLOCKED] Extreme heat detected in {location_name}, but no municipal server is connected to receive the warning.")
        return False
        
    try:
        requests.post(target_webhook_url, json=cap_payload, timeout=5)
        print(f"\n[🚨 EVENT-DRIVEN CAP ALERT TRIGGERED]")
        print(f"Routing to Connected Server : {target_webhook_url} ({matched_region})")
        print(f"Urgency                     : {urgency} (Peak MRI: {breach_mri})")
        return True
    except Exception as e:
        print(f"Webhook delivery failed: {e}")
        return False

def get_acclimatization_multiplier(lat, lon, current_temp):
    try:
        today = datetime.date.today()
        
        start_date = (today.replace(year=today.year - 5)).strftime('%Y-%m-%d')
        end_date = (today.replace(year=today.year - 1)).strftime('%Y-%m-%d')
        
        # Open-Meteo Historical Archive API
        base_url = current_app.config['OPEN_METEO_ARCHIVE_URL']
        url = f"{base_url}?latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}&daily=temperature_2m_max&timezone=auto"

        res = requests.get(url, timeout=5)
        res.raise_for_status()
        data = res.json()
        
        times = data.get("daily", {}).get("time", [])
        past_temps = data.get("daily", {}).get("temperature_2m_max", [])
        
        valid_temps = []
        target_month = today.month
        
        for date_str, t in zip(times, past_temps):
            if t is not None:
                record_month = int(date_str.split('-')[1])
                if record_month == target_month:
                    valid_temps.append(t)
        
        if not valid_temps:
            # Print a detailed warning to the Flask console before falling back
            print(f"⚠️ WARNING: No valid historical data found for month {target_month} between {start_date} and {end_date} at {lat}, {lon}")
            return 1.0  # Safe fallback if API has gaps
            
        # Now this is the true historical average for this specific month!
        historical_avg = sum(valid_temps) / len(valid_temps)
        
        # Is today hotter than the 5-year normal for this month?
        temp_anomaly = current_temp - historical_avg
        
        if temp_anomaly > 0:
            return round(1.0 + (temp_anomaly * 0.04), 2)
        else:
            return 1.0
            
    except Exception as e:
        print(f"Historical Acclimatization Error: {e}")
        return 1.0

def reverse_geocode(lat, lon):
    base_url = current_app.config['NOMINATIM_REVERSE_URL']
    url = f"{base_url}?lat={lat}&lon={lon}&format=json"

    headers = {"User-Agent": "SIH_MoES_Heatwave_App/1.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        address = data.get("address", {})
        
        # To get the most specific local name possible
        name = address.get("suburb") or address.get("neighbourhood") or address.get("city") or address.get("town") or "Local Area"
        
        return {
            "name": name,
            "lat": float(lat),
            "lon": float(lon),
            "admin1": address.get("state", "Unknown State"),
            "importance": 0.4
        }
    except Exception as e:
        print(f"Reverse geocode error: {e}")
        return None

def calculate_spatial_vulnerability(lat, lon, radius_meters=1500):
    offset = radius_meters / 111000.0
    slat, wlon = lat - offset, lon - offset
    nlat, elon = lat + offset, lon + offset

    overpass_mirrors = current_app.config['OVERPASS_MIRRORS']
    
    query = f"""
    [out:json][timeout:25];
    (
      /* High-Risk Zones */
      nwr["landuse"="industrial"]({slat},{wlon},{nlat},{elon});
      nwr["landuse"="construction"]({slat},{wlon},{nlat},{elon});
      
      /* Medium-Risk Zones (Dense human traffic) */
      nwr["landuse"="commercial"]({slat},{wlon},{nlat},{elon});
      nwr["landuse"="retail"]({slat},{wlon},{nlat},{elon});
      nwr["landuse"="residential"]({slat},{wlon},{nlat},{elon});
      
      /* Cooling Zones */
      nwr["leisure"="park"]({slat},{wlon},{nlat},{elon});
      nwr["landuse"="forest"]({slat},{wlon},{nlat},{elon});
    );
    out center;
    """
    
    headers = {"User-Agent": "SIH_MoES_Heatwave_App/1.0"}
    
    for url in overpass_mirrors:
        try:
            response = requests.post(url, data={'data': query}, headers=headers, timeout=25)
            if response.status_code == 200:
                data = response.json()
                high_risk_count = 0    # Industrial, Construction
                retail_count = 0       # Open-air markets, shops, bazaars (Chickpet)
                residential_count = 0  # Homes, Slums 
                commercial_count = 0   # IT Parks, Offices (Whitefield - AC Access)
                green_count = 0        # Parks, Forests
        
                for element in data.get('elements', []):
                    tags = element.get('tags', {})
                    landuse = tags.get('landuse')
                    leisure = tags.get('leisure')
                
                    if landuse in ['industrial', 'construction']:
                        high_risk_count += 1
                    elif landuse == 'retail':
                        retail_count += 1
                    elif landuse == 'residential':
                        residential_count += 1
                    elif landuse == 'commercial':
                        commercial_count += 1
                    elif leisure == 'park' or landuse == 'forest':
                        green_count += 1
                    
                # --- INDIA-SPECIFIC ADAPTIVE CAPACITY WEIGHTS ---
                
                # Industry/Labor: Brutal outdoor exposure (+0.03)
                # Retail/Markets: Dense foot traffic, open-air stalls, narrow streets (+0.02)
                # Residential: (+0.015)
                # Commercial/IT: High concrete, but indoor AC environment (+0.002)
                heat_penalty = min(
                    (high_risk_count * 0.15) + 
                    (retail_count * 0.02) + 
                    (residential_count * 0.005) + 
                    (commercial_count * 0.002), 
                    0.60
                ) 
                
                cooling_bonus = min(green_count * 0.01, 0.35)
                
                final_multiplier = 1.0 + heat_penalty - cooling_bonus
                
                print(f"Success on {url} for {lat}, {lon}")
                return round(final_multiplier, 2)
                
        except Exception as e:
            print(f"Mirror failed ({url}): {e}")
            continue 
            
    raise Exception("Live spatial analysis failed: Network unreachable or API blocked.")


def calculate_wbgt(temp, humidity, wind_kmh, solar_radiation=0.0):
    try:
        t = float(temp)
        rh = float(humidity)
        v_ms = max(float(wind_kmh) / 3.6, 0.1) 
        sol = max(float(solar_radiation or 0.0), 0.0)
        
        twb = (
            t * math.atan(0.151977 * math.sqrt(rh + 8.313659))
            + math.atan(t + rh)
            - math.atan(rh - 1.676331)
            + 0.00391838 * (rh ** 1.5) * math.atan(0.023101 * rh)
            - 4.686035
        )
        
        tg = t + (0.015 * sol) / (1.0 + 0.5 * v_ms)
        wbgt = (0.7 * twb) + (0.2 * tg) + (0.1 * t)
        return round(wbgt, 1)
    except Exception:
        return round(temp * 0.85, 1)

def get_risk_meta(wbgt, adjusted_stress):    
    if wbgt >= current_app.config['WBGT_EXTREME']:
        occ_dir = "Total suspension of outdoor physical labor; construction halted."
    elif wbgt >= current_app.config['WBGT_DANGER']:
        occ_dir = "Enforce mandatory 50% work-rest cycles; limit direct solar exposure."
    elif wbgt >= current_app.config['WBGT_CAUTION']:
        occ_dir = "Increase fluid intake; provide shaded hydration points for outdoor workers."
    else:
        occ_dir = "Standard outdoor working conditions. Routine hydration recommended."

    if adjusted_stress >= current_app.config['THRESHOLD_EXTREME']:
        return ("RED ALERT (Extreme Risk)", "danger", "#dc3545", occ_dir, "Critical mortality risk. Deploy emergency ambulances and open public cooling centers immediately.")
    elif adjusted_stress >= current_app.config['THRESHOLD_DANGER']:
        return ("ORANGE ALERT (High Risk)", "orange", "#fd7e14", occ_dir, "High hospitalization risk. Activate ward-level medical surge capacity and dispatch water tankers.")
    elif adjusted_stress >= current_app.config['THRESHOLD_CAUTION']:
        return ("YELLOW ALERT (Caution)", "warning", "#ffc107", occ_dir, "Elevated vulnerability. Issue public health warnings and monitor elderly/slum populations.")
    else:
        return ("GREEN (Normal)", "success", "#198754", occ_dir, "No elevated municipal emergency response required.")

def geocode_location(query):
    base_url = current_app.config['NOMINATIM_SEARCH_URL']
    geo_url = f"{base_url}?q={query}&countrycodes=in&layer=address&format=json&limit=1&addressdetails=1"
    headers = {"User-Agent": "SIH_MoES_Heatwave_App/1.0"}
    
    try:
        res = requests.get(geo_url, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        
        if len(data) > 0:
            result = data[0]
            return {
                "name": result.get("name", query.split(',')[0]),
                "lat": float(result.get("lat")),
                "lon": float(result.get("lon")),
                "admin1": result.get("address", {}).get("state", "Unknown State"),
                "importance": result.get("importance", 0.1) 
            }
    except Exception as e:
        print(f"Nominatim Geocoding error: {e}")
    return None

def fetch_dynamic_location(query=None, lat=None, lon=None):    
    if lat and lon:
        geo = reverse_geocode(lat, lon)
    else:
        geo = geocode_location(query)
        
    if not geo:
        return {"error": "Location not found in geospatial database. Try adding the state name."}
        
    lat, lon = geo['lat'], geo['lon']
    name = f"{geo['name']}, {geo['admin1']}"
    
    importance = geo.get('importance', 0.1)
    
    if importance > 0.7:
        dynamic_radius = 5000  # Mega-City
    elif importance > 0.5:
        dynamic_radius = 3000  # Normal City/District
    elif importance > 0.35:
        dynamic_radius = 1500  # Town/Large Suburb
    else:
        dynamic_radius = 800   # Village/Local Ward
        
    try:
        # 1. Fetch Spatial Multiplier (OSM)
        dynamic_multiplier = calculate_spatial_vulnerability(lat, lon, radius_meters=dynamic_radius)
        
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m,shortwave_radiation",
            "hourly": "temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m,shortwave_radiation",
            "forecast_days": 5,
            "timezone": current_app.config['TIMEZONE']
        }
        
        res = requests.get(current_app.config['OPEN_METEO_BASE_URL'], params=params, timeout=15)
        res.raise_for_status()
        data = res.json()
        
        cur = data.get('current', {})
        hourly = data.get('hourly', {})
        
        temp = cur.get('temperature_2m', 0.0)
        humidity = cur.get('relative_humidity_2m', 0.0)
        wind = cur.get('wind_speed_10m', 0.0)
        solar = cur.get('shortwave_radiation', 0.0)
        apparent_temp = cur.get('apparent_temperature', temp)
        
        # 2. Fetch the 5-year historical climate shock factor
        acclimatization_factor = get_acclimatization_multiplier(lat, lon, temp)
        
        # 3. Combine both multipliers (OSM Spatial x Historical Shock)
        final_mri_multiplier = dynamic_multiplier * acclimatization_factor
        
        # 4. Generate 5-Day Forecast using the FINAL multiplier
        hourly_times = hourly.get('time', [])
        hourly_temps = hourly.get('temperature_2m', [])
        hourly_rhs = hourly.get('relative_humidity_2m', [])
        hourly_winds = hourly.get('wind_speed_10m', [])
        hourly_sols = hourly.get('shortwave_radiation', [])
        
        forecast_mri_list = []
        for i in range(len(hourly_times)):
            t_h = hourly_temps[i] if i < len(hourly_temps) else temp
            rh_h = hourly_rhs[i] if i < len(hourly_rhs) else humidity
            w_h = hourly_winds[i] if i < len(hourly_winds) else wind
            s_h = hourly_sols[i] if i < len(hourly_sols) else 0.0
            
            hourly_wbgt = calculate_wbgt(t_h, rh_h, w_h, s_h)

            hourly_mri = round(hourly_wbgt * final_mri_multiplier, 1) 
            forecast_mri_list.append(hourly_mri)
            
        # 5. Calculate Current Metrics
        current_wbgt = calculate_wbgt(temp, humidity, wind, solar)
        adjusted_stress = round(current_wbgt * final_mri_multiplier, 1)
        
        risk_level, color, hex_color, occ_dir, mun_action = get_risk_meta(current_wbgt, adjusted_stress)

        dispatch_government_webhook(name, lat, lon, adjusted_stress, hourly_times, forecast_mri_list)
        
        return {
            "name": name,
            "lat": lat,
            "lon": lon,
            "scan_radius": dynamic_radius,
            "multiplier": round(final_mri_multiplier, 2),
            "temp": round(temp, 1),
            "humidity": round(humidity, 1),
            "wind": round(wind, 1),
            "wbgt": current_wbgt,
            "apparent_temp": round(apparent_temp, 1),
            "adjusted_stress": adjusted_stress,
            "risk_level": risk_level,
            "color": color,
            "hex_color": hex_color,
            "occ_directive": occ_dir,      
            "mun_action": mun_action,      
            "forecast_times": hourly_times,
            "forecast_temps": forecast_mri_list
        }
        
    except Exception as e:
        return {"error": f"Data Pipeline Failure: {str(e)}"}