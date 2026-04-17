from flask import Flask, render_template, request, redirect
import pandas as pd
import json
import os
import time
from datetime import datetime

app = Flask(__name__)

DATA_FILE = "assignments.json"

log = []

VOLTAGE = 400
MAX_CHARGERS = 10
CHARGING_POWER = 120
BATTERY_CAPACITY = 350

def load_assignments():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_assignments(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def load_bus_data():
    return pd.read_csv("bus_data.csv")

@app.route("/", methods=["GET", "POST"])
def index():

    assignments = load_assignments()
    df = load_bus_data()

    page = "welcome"
    search_result = None
    highlight_bus = None
    access = False
    error_message = None
    result_message = None
    warning_message = None

    if request.method == "POST":
        action = request.form.get("action")

        if action == "go_input":
            page = "input"

        elif action == "go_status":
            page = "status"

        elif action == "go_admin":
            page = "login"

        elif action == "login":
            if request.form.get("code") == "2026":
                page = "admin"
                access = True

        elif action == "reset":
            save_assignments({})
            log.clear()
            return redirect("/")

        elif action == "search_bus":
            page = "status"
            sid = request.form.get("search_id")

            if not sid or not sid.isdigit():
                error_message = "Bus findes ikke"

            elif int(sid) not in df["bus_id"].values:
                error_message = "Bus findes ikke"

            elif sid not in assignments:
                error_message = "Bus er ude at køre"

            else:
                search_result = assignments[sid]
                highlight_bus = sid

                # 🔥 FIXET WARNING LOGIK
                if (
                    not search_result.get("can_full_charge", True)
                    or search_result.get("battery_now", 0) < 80
                ):
                    warning_message = "Advarsel: Bus mangler strøm og kan ikke fuldføre ruten"

        elif action == "checkin":
            bus_id = request.form.get("bus_id")

            if not bus_id or not bus_id.isdigit():
                error_message = "Bus findes ikke"
                page = "input"

            elif int(bus_id) not in df["bus_id"].values:
                error_message = "Bus findes ikke"
                page = "input"

            elif bus_id in assignments:
                error_message = "Bus er allerede tilsluttet"
                page = "input"

            else:
                row = df[df["bus_id"] == int(bus_id)]

                new_bus = {
                    "bus_id": int(bus_id),
                    "time": int(row.iloc[0]["available_time"]),
                    "energy_needed": float(row.iloc[0]["energy_needed"]),
                    "timestamp": time.time()
                }

                assignments[bus_id] = new_bus
                save_assignments(assignments)

                log.append({
                    "bus_id": bus_id,
                    "time": datetime.now().strftime("%H:%M")
                })

                # plads 101/201
                taken = []
                for i, data in enumerate(assignments.values()):
                    charger = (i % 5) + 1
                    pos = 1 if i < 5 else 2
                    slot = 100 + charger if pos == 1 else 200 + charger
                    taken.append(slot)

                assigned = None
                for c in range(1, 6):
                    for p in [100, 200]:
                        if p + c not in taken:
                            assigned = p + c
                            break
                    if assigned:
                        break

                new_bus["slot"] = assigned
                result_message = f"Kør til plads {assigned}"
                page = "result"

    grid = {i: {1: None, 2: None} for i in range(1, 6)}

    total_power = 0
    total_energy = 0

    for i, data in enumerate(assignments.values()):
        charger = (i % 5) + 1
        pos = 1 if i < 5 else 2

        data["slot"] = 100 + charger if pos == 1 else 200 + charger

        if "energy_needed" not in data:
            data["energy_needed"] = 100

        elapsed = time.time() - data["timestamp"]
        total_time = data["time"]

        hours = total_time / 3600
        energy_possible = hours * CHARGING_POWER

        data["can_full_charge"] = energy_possible >= data["energy_needed"]

        progress = elapsed / max(1, total_time)
        battery = min(100, (progress * data["energy_needed"] / BATTERY_CAPACITY) * 100)

        data["battery_now"] = int(battery)

        remaining = max(0, total_time - elapsed)
        data["remaining_text"] = f"{int(remaining//3600)}t {int((remaining%3600)//60)}m"

        total_power += CHARGING_POWER
        total_energy += (elapsed / 3600) * CHARGING_POWER

        grid[charger][pos] = data

    ampere = int(total_power * 1000 / VOLTAGE)

    return render_template(
        "index.html",
        page=page,
        grid=grid,
        search_result=search_result,
        highlight_bus=highlight_bus,
        total_power=int(total_power),
        total_energy=int(total_energy),
        ampere=ampere,
        active=len(assignments),
        max_chargers=MAX_CHARGERS,
        access=access,
        log=log,
        error_message=error_message,
        result_message=result_message,
        warning_message=warning_message
    )

if __name__ == "__main__":
    app.run(debug=True)