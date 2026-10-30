import pandas as pd
import numpy as np


def load_energy_data(path):
    df = pd.read_excel(path)
    df.columns = df.columns.astype(str).str.strip().str.lower()
    return df


def detect_column(columns, keywords):
    for col in columns:
        col_lower = str(col).lower().strip()
        for key in keywords:
            if key in col_lower:
                return col
    return None


def normalize_country(country):
    if pd.isna(country):
        return country
    country = str(country).strip()
    mapping = {
        "united states of america": "United States",
        "united states": "United States",
        "russian federation": "Russia",
        "viet nam": "Vietnam",
        "turkiye": "Turkey",
        "czech republic": "Czechia",
        "south korea": "South Korea",
        "north korea": "North Korea"
    }
    return mapping.get(country.lower(), country)


ENERGY_CATEGORIES = {
    "Biofuel": "biofuel_consumption",
    "Coal": "coal_consumption",
    "Electricity": "electricity_generation",
    "Fossil Fuel": "fossil_fuel_consumption",
    "Gas": "gas_consumption",
    "Hydro": "hydro_consumption",
    "Low Carbon": "low_carbon_consumption",
    "Nuclear": "nuclear_consumption",
    "Oil": "oil_consumption",
    "Renewable": "renewables_consumption",
    "Solar": "solar_consumption",
    "Wind": "wind_consumption",
    "CO2 Emissions": "greenhouse_gas_emissions",
    "Primary Energy": "primary_energy_consumption",
}

ENERGY_UNIT = {
    "Biofuel": "TWh",
    "Coal": "TWh",
    "Electricity": "TWh",
    "Fossil Fuel": "TWh",
    "Gas": "TWh",
    "Hydro": "TWh",
    "Low Carbon": "TWh",
    "Nuclear": "TWh",
    "Oil": "TWh",
    "Renewable": "TWh",
    "Solar": "TWh",
    "Wind": "TWh",
    "CO2 Emissions": "MtCO₂",
    "Primary Energy": "TWh",
}

PER_CAPITA_COLS = {
    "energy_per_capita": "Energi per Kapita (kWh/orang)",
    "biofuel_cons_per_capita": "Biofuel per Kapita (kWh)",
    "coal_cons_per_capita": "Batu Bara per Kapita (kWh)",
    "fossil_energy_per_capita": "Energi Fosil per Kapita (kWh)",
    "gas_energy_per_capita": "Gas per Kapita (kWh)",
    "hydro_energy_per_capita": "Hidro per Kapita (kWh)",
    "low_carbon_energy_per_capita": "Energi Rendah Karbon per Kapita (kWh)",
    "nuclear_energy_per_capita": "Nuklir per Kapita (kWh)",
    "oil_energy_per_capita": "Minyak per Kapita (kWh)",
    "renewables_energy_per_capita": "EBT per Kapita (kWh)",
    "solar_energy_per_capita": "Surya per Kapita (kWh)",
    "wind_energy_per_capita": "Angin per Kapita (kWh)",
    "per_capita_electricity": "Listrik per Kapita (kWh)",
    "electricity_demand_per_capita": "Permintaan Listrik per Kapita (kWh)",
}


def get_energy_columns(df):
    available = {}
    for category, column in ENERGY_CATEGORIES.items():
        if column in df.columns:
            available[category] = column
    return available


def preprocess_data(energy):
    df = energy.copy()
    country_col = detect_column(df.columns, ["country", "entity"])
    if country_col is None:
        country_col = df.columns[0]
    year_col = detect_column(df.columns, ["year"])
    if year_col is None:
        raise ValueError("Kolom year tidak ditemukan.")
    df = df.rename(columns={country_col: "country", year_col: "year"})
    df["country"] = df["country"].astype(str).apply(normalize_country)
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    if "population" not in df.columns:
        raise ValueError("Kolom population tidak ditemukan di file energi.")
    df["population"] = pd.to_numeric(df["population"], errors="coerce")
    ignore_cols = ["country", "year", "iso_code"]
    for col in df.columns:
        if col not in ignore_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    possible_energy = [
        col for col in df.columns
        if ("consumption" in col.lower() or "energy" in col.lower())
        and col not in ignore_cols
    ]
    df["energy"] = df[possible_energy[0]] if possible_energy else np.nan
    df["energy_per_capita"] = np.where(
        (df["population"] > 0) & (df["energy"].notna()),
        df["energy"] / df["population"],
        np.nan
    )
    df = df.replace([np.inf, -np.inf], np.nan)
    return df


def generate_country_insight(value, energy_type):
    if pd.isna(value) or value == 0:
        return f"Data {energy_type} tidak tersedia atau bernilai nol."
    try:
        value = float(value)
    except:
        return f"Data {energy_type} tidak valid."
    if value > 500:
        return f"{energy_type} sangat tinggi — konsumsi besar."
    elif value > 100:
        return f"{energy_type} berada pada level tinggi."
    elif value > 10:
        return f"{energy_type} tergolong moderat."
    else:
        return f"{energy_type} relatif rendah."


def generate_global_insight(df, energy_metric, energy_type):
    insights = []
    try:
        df_clean = df.dropna(subset=[energy_metric, "country"])
        df_clean = df_clean[df_clean[energy_metric] > 0]
        if df_clean.empty:
            return ["Dataset tidak memiliki data valid untuk kategori ini."]
        sorted_df = df_clean.sort_values(energy_metric, ascending=False)
        top_country = sorted_df.iloc[0]["country"]
        top_value = sorted_df.iloc[0][energy_metric]
        bottom_country = sorted_df.iloc[-1]["country"]
        bottom_value = sorted_df.iloc[-1][energy_metric]
        total_energy = df_clean[energy_metric].sum()
        avg_energy = df_clean[energy_metric].mean()
        insights.append(f"Negara tertinggi: {top_country} dengan {energy_type} sebesar {top_value:,.2f}.")
        insights.append(f"{bottom_country} memiliki {energy_type} terendah ({bottom_value:,.2f}).")
        insights.append(f"Total konsumsi global {energy_type}: {total_energy:,.2f}.")
        insights.append(f"Rata-rata {energy_type} per negara: {avg_energy:,.2f}.")
    except Exception as e:
        insights.append(f"Gagal membuat insight: {e}")
    return insights
