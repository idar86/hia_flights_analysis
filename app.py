from datetime import datetime
import math
import streamlit as st
import requests
import json
import pandas as pd

st.set_page_config(layout="wide")

session = requests.session()

def todays_timestamp():
    current_datetime = datetime.now()
    end_of_today = current_datetime.replace(hour=23, minute=59, second=59, microsecond=999999)
    end_today_timestamp = end_of_today.timestamp()
    return end_today_timestamp

def get_flights_history(flight_type, start_ts, end_ts, limit):
    cookies = {
        'BIGipServerdohahamadairport-rhel7-pool': '771757228.20480.0000',
        'TS0123234d': '01925f569d2111310d2eab91b92299e721534113a4d59b1574f7db946068e487b399e4b62e4bdb79a6560c3af58f5828239f0a6670625f618da7bbd1537ce2fec0bbbd262d',
        'ln_or': 'eyI1NjcyMDgxIjoiZCJ9',
        '_ga': 'GA1.2.2128900892.1694957465',
        '_gid': 'GA1.2.873414632.1694957465',
        '_gat_UA-50467329-3': '1',
    }

    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://dohahamadairport.com',
        'Referer': 'https://dohahamadairport.com/airlines/flight-status?type=arrivals&day=yesterday&airline=all&locate=all&search_key=',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'sec-ch-ua': '"Chromium";v="116", "Not)A;Brand";v="24", "Google Chrome";v="116"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    }
    
    data = {
        "limit": limit,
        "startTime": str(start_ts),
        "endTime": str(end_ts)
    }
    
    params = {
    't': '1694957446666',
    }

    data = json.dumps(data)

    try:
        response = session.post(
            f'https://dohahamadairport.com/webservices/fids/{flight_type}',
            params=params,
            cookies=cookies,
            headers=headers,
            data=data,
        )
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
    except requests.RequestException as e:
        st.error(f"Error fetching data from the API: {e}")
        return None

    if response.status_code == 200:
        return response.json()

# Function to fetch data from the API

@st.cache_data
def fetch_data(request_days, flight_type, limit):
    ts = todays_timestamp() + 86400
    seconds = request_days * 86400
    
    start_ts = math.ceil(ts - seconds)
    end_ts = int(ts)
    ts = ts - seconds
    
    data = get_flights_history(flight_type, start_ts, end_ts, limit)
    data = data['flights']

    for rec in data:
        lang = rec.pop('lang', None)
        if lang:
            en = lang.pop('en', None)
            if en:
                rec.update(en)
    
    return data

@st.cache_data
def get_scheduled_flights():
    start_ts = todays_timestamp() - 84600
    end_ts = start_ts + (84600 * 2)
    limit = 5000
    flights_data = []
    data = get_flights_history('departures', start_ts, end_ts, limit)
    if data:
        flights_data += data.get('flights')
    data = get_flights_history('arrivals', start_ts, end_ts, limit)
    if data:
        flights_data += data.get('flights')
    
    scheduled_flights = []
    print(len(flights_data))
    if flights_data:
        for flight in flights_data:
            if flight.get('lang').get('en').get('flightStatus') == 'Scheduled':
                lang = flight.pop('lang', None)
                if lang:
                    en = lang.pop('en', None)
                    if en:
                        flight.update(en)
                scheduled_flights.append(flight)
    return scheduled_flights

def display_data(data, ftype=None, request_days=None, raw=False):

    if ftype and request_days:
        st.header(f"Flight {ftype} History")
        st.subheader(f"Showing data for the last {request_days} days")

    else:
        st.header('Scheduled flight')
    
    if data:
        if not raw:
            # Allow the user to select columns to display
            selected_columns = st.sidebar.multiselect("Select columns to display", data[0].keys(), default=data[0].keys())

            data_df = pd.json_normalize(data)

            # Convert specific columns to datetime if they are in timestamp format
            # timestamp_columns = [col for col in data_df.columns if 'time' in col.lower()]  # Add your timestamp columns here
            # for col in timestamp_columns:
            #     if col in data_df.columns:
            #         data_df[col] = pd.to_datetime(data_df[col], origin='unix', unit='s', errors='coerce')

            data_df = data_df[selected_columns]
            if 'flightStatus' in selected_columns:
                fstatus = data_df.pop('flightStatus')
                data_df.insert(2, 'flightStatus', fstatus)
            st.table(data_df)
        else:
            st.write(data)

# Streamlit App
def main():
    st.title("API Data Scraping and Dashboard")
    
    # Sidebar for user inputs
    st.sidebar.header("Filters")
    ftype = st.sidebar.radio("Flight Type", options=["Arrivals 🛬", "Departures 🛫"], index=0)
    ftype = ftype.lower().split(' ')[0].strip()
    request_days = st.sidebar.slider("Select the number of days", min_value=1, max_value=30, value=1)
    limit = st.sidebar.slider("Select the limit of flights", min_value=1, max_value=5000, value=10)
    raw = st.checkbox("Show RAW data")

    if st.sidebar.button('Get Scheduled Flight'):
        flights = get_scheduled_flights()
        if flights:
            display_data(flights, raw=raw)
    
    # Fetch data from the API
    data = fetch_data(request_days, ftype, limit)
    if data:
        display_data(data, ftype, request_days, raw=raw)

if __name__ == "__main__":
    main()
