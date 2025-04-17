import csv
import logging
from io import StringIO

import pandas as pd

_logger = logging.getLogger(__name__)

# Raw data (paste the content here)
data = """your raw data here"""


file = "/Volumes/USBSSD/_scripts/doodba/odoo/custom/src/Odoo-RZL/datev_at/misc/sample.csv"
file = "/Volumes/USBSSD/_scripts/doodba/odoo/custom/src/Odoo-RZL/datev_at/misc/original.csv"
# Read the data into a DataFrame

with open(file) as f:
    data = f.read()

lines = data.split("\\r\\n")

first_line = lines[0]

data = "\n".join(lines[1:])

df = pd.read_csv(StringIO(data), sep=";", header=0, dtype=str)  # skiprows=1,

# Extract column names from the second row (assuming first row is metadata)
# column_names = df.iloc[1].tolist()
# df.columns = column_names

_logger.info(df.head(5))
# Drop the first two rows as they are metadata
# df = df.iloc[2:].reset_index(drop=True)

# Convert numeric columns
df["Umsatz (ohne Soll/Haben-Kz)"] = df["Umsatz (ohne Soll/Haben-Kz)"].str.replace(",", ".").astype(float)

_logger.info(df.columns)
# Grouping based on specified columns

custom_order = df.columns.tolist()
grouped_fields = df.columns.tolist()
agg_fields = [
    "Umsatz (ohne Soll/Haben-Kz)",
    "Soll/Haben-Kennzeichen",
    "WKZ Umsatz",
    "Buchungstext",
]

for item in agg_fields:
    while item in grouped_fields:
        grouped_fields.remove(item)

gr_by = [
    "Konto",
    "Gegenkonto (ohne BU-Schlüssel)",
    "BU-Schlüssel",
    "Belegdatum",
    "Belegfeld 1",
    "Kurs",
]

grouped_df = df.groupby(
    # gr_by,
    grouped_fields,
    as_index=False,
    dropna=False,
).agg(
    {
        "Umsatz (ohne Soll/Haben-Kz)": "sum",  # Sum amounts
        "Soll/Haben-Kennzeichen": "first",  # Keep the first encountered value
        "WKZ Umsatz": "first",  # Keep the first encountered value
        # "Buchungstext": "first"  # Keep the first encountered value
        "Buchungstext": lambda x: " | ".join(x.dropna().unique()),  # Concatenate unique texts
        # Add more aggregations as needed
    }
)
grouped_df = grouped_df[custom_order]
_logger.info(grouped_df.head(5))

# Convert the amount back to string with comma as decimal separator
grouped_df["Umsatz (ohne Soll/Haben-Kz)"] = grouped_df["Umsatz (ohne Soll/Haben-Kz)"].apply(
    lambda x: f"{x:.2f}".replace(".", ",")
)

# Convert back to CSV-like format
output_data = grouped_df.to_csv(sep=";", index=False, quoting=csv.QUOTE_ALL, lineterminator="\r\n")

final_data = first_line + "\n" + output_data

# Display transformed output
with open(
    "/Volumes/USBSSD/_scripts/doodba/odoo/custom/src/Odoo-RZL/datev_at/misc/output.csv",
    "w",
) as f:
    f.write(final_data)
