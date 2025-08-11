# streamlit_app.py
import os, requests, pandas as pd, streamlit as st

API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:7071/api")  # Local

st.set_page_config(page_title="WeatherCast", page_icon="🌤️", layout="centered")
st.title("WeatherCast 🌤️")

@st.cache_data(ttl=300, show_spinner=False)
def fetch_report(city: str, days: int) -> dict:
    url = f"{API_BASE}/WeatherReport?city={city}&days={int(days)}"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()

col1, col2 = st.columns([2,1])
with col1:
    city = st.text_input("City", value="Vancouver")
with col2:
    days = st.number_input("#Day", 1, 5, value=3, step=1)

if st.button("CHECK"):
    try:
        # cahce --> no connection to api
        data = fetch_report(city, int(days))

        st.caption(f"Generated time（UTC）: {data['generated_at_utc']}")
        tips = data.get("tips", [])
        if tips: st.success("；".join(tips))
        else:    st.info("No suggestion")

        df = pd.DataFrame(data.get("forecast", []))
        if not df.empty:
            st.dataframe(df)
            st.line_chart(df.set_index("date")[["temp_min_c", "temp_max_c"]])
        else:
            st.warning("No forecast")
    except Exception as e:
        st.error(f"Load failed：{e}")