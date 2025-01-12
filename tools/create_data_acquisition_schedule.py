import os
from datetime import datetime, timedelta

import pandas as pd

# Define the start and end dates
earliest_date = datetime(2010, 1, 1)
latest_date = datetime(2024, 12, 31)

# Initialize an empty list to store the periods
periods = []

# Loop through the years and create the periods
current_date = earliest_date
while current_date <= latest_date:
    # Create the January 1 to June 30 period
    start = datetime(current_date.year, 1, 1)
    end = datetime(current_date.year, 12, 31)
    periods.append({"start_date": start, "end_date": end})
    # Move to the next year
    current_date = current_date.replace(year=current_date.year + 1)

# Create a DataFrame from the periods list
df = pd.DataFrame(periods)

# Define acquisition dates
acquisition_start_date = datetime(2025, 1, 13)

acquisition_dates = [acquisition_start_date + timedelta(days=i) for i in range(len(df))]
df["acquisition_date"] = acquisition_dates

df = df[["acquisition_date", "start_date", "end_date"]]

current_dir = os.path.dirname(os.path.abspath(__file__))

df.to_csv(f"{current_dir}/acquisition_dates.csv", index=False)
