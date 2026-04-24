import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from geopy.geocoders import Nominatim
from pdf_report import generate_pdf

# ------------------------------
# PAGE CONFIG
# ------------------------------
st.set_page_config(page_title="AQI Dashboard", layout="wide")
st.title("🌿 Advanced AQI Dashboard")

# ------------------------------
# LOAD DATA
# ------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv("city_day.csv")
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.dropna(subset=["AQI"])
    return df

df = load_data()

# ------------------------------
# API KEY
# ------------------------------
API_KEY = st.secrets.get("OPENWEATHER_API_KEY", "")

@st.cache_data(ttl=300)
def get_real_time_aqi(lat, lon):
    if not API_KEY:
        return None
    url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}"
    r = requests.get(url)
    if r.status_code == 200:
        return r.json()["list"][0]
    return None

# ------------------------------
# GEOCODING
# ------------------------------
@st.cache_data
def geocode_city(city):
    geolocator = Nominatim(user_agent="aqi_app")
    return geolocator.geocode(city)

# ------------------------------
# SIDEBAR
# ------------------------------
st.sidebar.header("Filters")

cities = df["City"].dropna().unique()

selected_cities = st.sidebar.multiselect(
    "Select City",
    options=cities,
    default=[cities[0]]
)

start_date = st.sidebar.date_input("Start Date", df["Date"].min())
end_date = st.sidebar.date_input("End Date", df["Date"].max())

filtered_data = df[
    (df["City"].isin(selected_cities)) &
    (df["Date"] >= pd.to_datetime(start_date)) &
    (df["Date"] <= pd.to_datetime(end_date))
].copy()

pollutants = ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3"]

# ------------------------------
# LIVE AQI INPUT
# ------------------------------
city_input = st.sidebar.text_input("Enter City (Live AQI)")

lat, lon = None, None

if city_input:
    loc = geocode_city(city_input)
    if loc:
        lat, lon = float(loc.latitude), float(loc.longitude)

# ------------------------------
# LIVE AQI SECTION
# ------------------------------
st.subheader("🌍 Live AQI Dashboard")

if lat and lon:
    data = get_real_time_aqi(lat, lon)

    if data:
        aqi_val = float(data["main"]["aqi"])

        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            st.markdown(
                f"""
                <div style="
                    padding:25px;
                    border-radius:18px;
                    text-align:center;
                    background:linear-gradient(135deg,#0f2027,#203a43,#2c5364);
                    color:white;
                    box-shadow:0px 6px 20px rgba(0,0,0,0.25);
                ">
                    <h2>Current AQI</h2>
                    <h1 style="font-size:60px;margin:0;">{aqi_val}</h1>
                </div>
                """,
                unsafe_allow_html=True
            )

        category_map = {
            1: "Good",
            2: "Fair",
            3: "Moderate",
            4: "Poor",
            5: "Very Poor"
        }

        st.info(f"Status: {category_map.get(aqi_val, 'Unknown')}")

        st.subheader("🧪 Pollutants")

        cols = st.columns(3)
        for i, (k, v) in enumerate(data["components"].items()):
            with cols[i % 3]:
                st.metric(k.upper(), round(v, 2))

# ------------------------------
# SUMMARY
# ------------------------------
st.subheader("📊 Summary")

if not filtered_data.empty:
    c1, c2, c3 = st.columns(3)
    c1.metric("Avg AQI", int(filtered_data["AQI"].mean()))
    c2.metric("Max AQI", int(filtered_data["AQI"].max()))
    c3.metric("Min AQI", int(filtered_data["AQI"].min()))

# ------------------------------
# AQI TREND
# ------------------------------
st.subheader("📈 AQI Trend")

if not filtered_data.empty:
    fig = px.line(filtered_data, x="Date", y="AQI", color="City")
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------
# POLLUTANT TREND
# ------------------------------
st.subheader("🧪 Pollutant Trends")

if not filtered_data.empty:
    pol = st.selectbox("Select Pollutant", pollutants)
    fig = px.line(filtered_data, x="Date", y=pol, color="City")
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------
# POLLUTANT SOURCES
# ------------------------------
def get_pollutant_sources(row):
    return {
        "PM2.5": {
            "Vehicular": row["PM2.5"] * 0.35,
            "Industrial": row["PM2.5"] * 0.25,
            "Biomass": row["PM2.5"] * 0.20,
            "Dust": row["PM2.5"] * 0.20
        },
        "PM10": {
            "Dust": row["PM10"] * 0.50,
            "Construction": row["PM10"] * 0.20,
            "Vehicular": row["PM10"] * 0.20,
            "Industrial": row["PM10"] * 0.10
        },
        "NO2": {
            "Vehicular": row["NO2"] * 0.60,
            "Industrial": row["NO2"] * 0.40
        },
        "SO2": {
            "Industrial": row["SO2"] * 0.70,
            "Power Plants": row["SO2"] * 0.30
        },
        "CO": {
            "Combustion": row["CO"] * 0.70,
            "Vehicular": row["CO"] * 0.30
        },
        "O3": {
            "Photochemical": row["O3"]
        }
    }

st.subheader("🔬 Pollutant Source Analysis")

if not filtered_data.empty:
    latest = filtered_data.iloc[-1]
    sources = get_pollutant_sources(latest)

    pol = st.selectbox("Select Pollutant Source", list(sources.keys()))

    src_df = pd.DataFrame({
        "Source": sources[pol].keys(),
        "Value": sources[pol].values()
    })

    col1, col2 = st.columns(2)

    with col1:
        st.dataframe(src_df)

    with col2:
        fig = px.pie(src_df, names="Source", values="Value")
        st.plotly_chart(fig, use_container_width=True)

# ------------------------------
# MAP
# ------------------------------
st.subheader("🗺️ AQI Map")

if not filtered_data.empty:
    latest = filtered_data.groupby("City").tail(1)

    fig = px.scatter(latest, x="City", y="AQI", size="AQI", color="AQI")
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------
# CITY COMPARISON
# ------------------------------
st.subheader("⚔️ City Comparison")

if len(selected_cities) >= 2:
    comp = filtered_data.groupby("City")["AQI"].mean().reset_index()
    st.dataframe(comp)

    fig = px.bar(comp, x="City", y="AQI", color="City")
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------
# HEALTH ADVICE
# ------------------------------
st.subheader("🩺 Health Advice")

if not filtered_data.empty:
    aqi = filtered_data.iloc[-1]["AQI"]

    if aqi > 300:
        st.error("Avoid outdoor activity")
    elif aqi > 200:
        st.warning("Wear mask")
    elif aqi > 100:
        st.info("Sensitive groups should be careful")
    else:
        st.success("Good air quality")

# ------------------------------
# PDF EXPORT
# ------------------------------
st.subheader("📄 Export Report")

if st.button("Generate PDF") and not filtered_data.empty:
    file = generate_pdf(filtered_data)

    with open(file, "rb") as f:
        st.download_button(
            "Download PDF",
            f,
            file_name="AQI_Report.pdf",
            mime="application/pdf"
        )