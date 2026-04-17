import pandas as pd
import numpy as np

np.random.seed(42)

n = 50

data = []

for i in range(1, n+1):
    battery_level = np.random.uniform(0.2, 0.8)  # 🔋 20-80%

    capacity = 350

    energy_needed = (1 - battery_level) * capacity

    charge_time = energy_needed / 120 * 3600  # sek

    available_time = charge_time * np.random.uniform(0.6, 1.2)

    # 🔥 TILFØJET battery_start i %
    battery_percent = int(battery_level * 100)

    data.append([i, int(available_time), energy_needed, battery_percent])

df = pd.DataFrame(
    data,
    columns=["bus_id", "available_time", "energy_needed", "battery_start"]
)

df.to_csv("bus_data.csv", index=False)

print("CSV klar")