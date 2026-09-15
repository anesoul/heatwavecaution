import math
import datetime
import requests
from flask import current_app

def reverse_geocode(lat, lon):
    """Translates raw browser GPS coordinates into a readable location name."""
    url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
    headers = {"User-Agent": "SIH_MoES_Heatwave_App/1.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        address = data.get("address", {})
        
        # Try to get the most specific local name possible
        name = address.get("suburb") or address.get("neighbourhood") or address.get("city") or address.get("town") or "Local Area"
        
        return {
            "name": name,
            "lat": float(lat),
            "lon": float(lon),
            "admin1": address.get("state", "Unknown State"),
            "importance": 0.4 # Default to a 1.5km town radius for user location
        }
    except Exception as e:
        print(f"Reverse geocode error: {e}")
        return None

def calculate_spatial_vulnerability(lat, lon, radius_meters=1500):
    """Calculates spatial vulnerability. NO FALLBACKS. Raises error if it fails."""
    offset = radius_meters / 111000.0
    slat, wlon = lat - offset, lon - offset
    nlat, elon = lat + offset, lon + offset
    
    # Using multiple mirrors to bypass strict firewalls
    overpass_mirrors = [
        "https://overpass-api.de/api/interpreter",
        "https://lz4.overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter"
    ]
    
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
                # Residential: High nighttime exposure (+0.015)
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
            
    # CRITICAL: We intentionally crash the function to trigger the flash message!
    raise Exception("Live spatial analysis failed: Network unreachable or API blocked.")


def calculate_wbgt(temp, humidity, wind_kmh, solar_radiation=0.0):
    """
    Calculates outdoor Wet-Bulb Globe Temperature (WBGT).
    """
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
    """Determines risk level, UI color, and split advisories based on dual thresholds."""
    
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

'''
def fetch_bengaluru_weather():
    """Initial load function for the dashboard landing page."""
    base_url = current_app.config['OPEN_METEO_BASE_URL']
    wards = current_app.config['WARDS_DATA']
    
    ward_results = {}
    
    for name, info in wards.items():
        params = {
            "latitude": info['lat'],
            "longitude": info['lon'],
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m,shortwave_radiation",
            "hourly": "temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m,shortwave_radiation",
            "forecast_days": 5,
            "timezone": current_app.config['TIMEZONE']
        }
        
        # Provide a safe landing page load (keeps app from crashing on boot if internet drops)
        try:
            dynamic_multiplier = calculate_spatial_vulnerability(info['lat'], info['lon'])
        except Exception:
            dynamic_multiplier = info.get('fallback_multiplier', 1.0)
        
        try:
            res = requests.get(base_url, params=params, timeout=15)
            res.raise_for_status()
            data = res.json()
            
            cur = data.get('current', {})
            hourly = data.get('hourly', {})
            
            temp = cur.get('temperature_2m', 0.0)
            humidity = cur.get('relative_humidity_2m', 0.0)
            wind = cur.get('wind_speed_10m', 0.0)
            solar = cur.get('shortwave_radiation', 0.0)
            apparent_temp = cur.get('apparent_temperature', temp)
            
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
                hourly_mri = round(hourly_wbgt * dynamic_multiplier, 1)
                forecast_mri_list.append(hourly_mri)
                
        except Exception as e:
            print(f"API Error for {name}: {e}")
            temp, humidity, wind, solar, apparent_temp = 30.0, 55.0, 10.0, 400.0, 33.0
            base_time = datetime.datetime.now()
            hourly_times = [(base_time + datetime.timedelta(hours=i)).isoformat() for i in range(120)]
            forecast_mri_list = [round((25.0 + (math.sin(i / 3.8) * 4)) * dynamic_multiplier, 1) for i in range(120)]

        current_wbgt = calculate_wbgt(temp, humidity, wind, solar)
        adjusted_stress = round(current_wbgt * dynamic_multiplier, 1)
        risk_level, color, hex_color, occ_dir, mun_action = get_risk_meta(current_wbgt, adjusted_stress)
        
        ward_results[name] = {
            "name": name,
            "desc": info.get("desc", ""),
            "lat": info['lat'],
            "lon": info['lon'],
            "multiplier": dynamic_multiplier,
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

    primary_key = "Sampangi Rama Nagar" if "Sampangi Rama Nagar" in ward_results else list(ward_results.keys())[0]
    active_ward = ward_results[primary_key]

    return {
        "active": active_ward,
        "all_wards": list(ward_results.values()),
        "ward_map": ward_results
    }
'''

def geocode_location(query):
    """Hits the OpenStreetMap Nominatim API for hyper-accurate local ward/street geocoding."""
    geo_url = f"https://nominatim.openstreetmap.org/search?q={query}&countrycodes=in&layer=address&format=json&limit=1&addressdetails=1"
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
    """Fetches data based on text query OR exact GPS coordinates. NO FALLBACKS."""
    
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
        dynamic_radius = 3000  # Normal City / District
    elif importance > 0.35:
        dynamic_radius = 1500  # Town / Large Suburb
    else:
        dynamic_radius = 800   # Village / Local Ward
        
    try:
        # If OSM is down, this throws an error and jumps to the except block instantly
        dynamic_multiplier = calculate_spatial_vulnerability(lat, lon, radius_meters=dynamic_radius)
        
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m,shortwave_radiation",
            "hourly": "temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m,shortwave_radiation",
            "forecast_days": 5,
            "timezone": current_app.config['TIMEZONE']
        }
        
        # If Weather API is down, this throws an error and jumps to the except block instantly
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
            hourly_mri = round(hourly_wbgt * dynamic_multiplier, 1)
            forecast_mri_list.append(hourly_mri)
            
        current_wbgt = calculate_wbgt(temp, humidity, wind, solar)
        adjusted_stress = round(current_wbgt * dynamic_multiplier, 1)
        risk_level, color, hex_color, occ_dir, mun_action = get_risk_meta(current_wbgt, adjusted_stress)
        
        return {
            "name": name,
            "lat": lat,
            "lon": lon,
            "scan_radius": dynamic_radius,
            "multiplier": dynamic_multiplier,
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
        # NO MORE FALLBACK DATA. RETURN THE ACTUAL ERROR TO THE UI!
        return {"error": f"Data Pipeline Failure: {str(e)}"}