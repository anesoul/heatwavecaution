from flask import Flask
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

from app import routes

import os
from apscheduler.schedulers.background import BackgroundScheduler

from app.utils import fetch_dynamic_location

def monitor_subscribed_regions():
    with app.app_context():
        from app.routes import registered_webhooks
        
        if not registered_webhooks:
            return
            
        print("\n[🕒 RADAR SWEEP] Running background monitoring for connected municipalities...")
        
        for region, url in registered_webhooks.items():
            print(f"--> Scanning {region}...")
            try:
                fetch_dynamic_location(query=region)
            except Exception as e:
                print(f"Failed background scan for {region}: {e}")

if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=monitor_subscribed_regions, trigger="interval", seconds=10)
    scheduler.start()