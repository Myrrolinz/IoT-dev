from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone

app = Flask(__name__)
# CORS(app)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:8080"}})

locations = {
    'Kendeda': {
        'indoor': {
            'Arcalis': 2580816
        },
        'outdoor': {
            'Atlas': 2099116
        }
    },
    'CNES': {
        'indoor': {
            'Antares': 2027273,
            'Arcalis': 2580816,
            'Alcyone': 2099110,
            'Asterope': 2099111
        },
        'outdoor': {
            'Atlas': 2099116
        }
    },
    'East Point': {
        'indoor': {
            'Asterope': 2099111
        },
        'outdoor': {
            'Atlas': 2099116
        }
    },
}

fields = {
    'co2': 4,
    'temperature': 5,
    'humidity': 6,
    'pressure': 7
}

read_api_key = 'XHA11H2XAGGWMDY1'
num_results = 8000

def fetch_data_from_thingspeak(channel_id, field):
    url = f"https://api.thingspeak.com/channels/{channel_id}/fields/{field}.json?results={num_results}&api_key={read_api_key}"
    response = requests.get(url)
    data = response.json()
    feeds = data['feeds']

    df = pd.DataFrame(feeds)
    df['created_at'] = pd.to_datetime(df['created_at'], utc=True)
    df['value'] = pd.to_numeric(df[f'field{field}'], errors='coerce')
    df = df.dropna()
    
    return df

def parse_date_range(range_str):
    now = datetime.now(timezone.utc)
    if range_str.endswith('d'):
        days = int(range_str[:-1])
        start_date = now - timedelta(days=days)
    elif range_str.endswith('m'):
        months = int(range_str[:-1])
        start_date = now - timedelta(days=30 * months)
    elif range_str.endswith('y'):
        years = int(range_str[:-1])
        start_date = now.replace(year=now.year - years)
    else:
        start_date = now - timedelta(days=7)
    end_date = now
    return start_date, end_date

def compute_delta(location, field, indoor_sensor_name, outdoor_sensor_name):
    indoor_channel_id = locations[location]['indoor'].get(indoor_sensor_name)
    if indoor_channel_id is None:
        raise ValueError(f"Indoor sensor {indoor_sensor_name} not found in location {location}")

    outdoor_channel_id = locations[location]['outdoor'].get(outdoor_sensor_name)
    if outdoor_channel_id is None:
        raise ValueError(f"Outdoor sensor {outdoor_sensor_name} not found in location {location}")

    indoor_data = fetch_data_from_thingspeak(indoor_channel_id, field)
    outdoor_data = fetch_data_from_thingspeak(outdoor_channel_id, field)

    if indoor_data.empty or outdoor_data.empty:
        raise ValueError("No data available for one or both sensors in the specified range")

    start_date = max(indoor_data['created_at'].min(), outdoor_data['created_at'].min())
    end_date = min(indoor_data['created_at'].max(), outdoor_data['created_at'].max())

    indoor_data = indoor_data[(indoor_data['created_at'] >= start_date) & (indoor_data['created_at'] <= end_date)]
    outdoor_data = outdoor_data[(outdoor_data['created_at'] >= start_date) & (outdoor_data['created_at'] <= end_date)]

    # Resample to 10-minute intervals
    indoor_data_resampled = indoor_data.set_index('created_at').resample('10T').mean(numeric_only=True)
    outdoor_data_resampled = outdoor_data.set_index('created_at').resample('10T').mean(numeric_only=True)

    # Detect gaps (periods with NaN values before interpolation)
    indoor_gaps = indoor_data_resampled['value'].isna().sum()
    outdoor_gaps = outdoor_data_resampled['value'].isna().sum()

    # Track which points are interpolated
    indoor_is_interpolated = indoor_data_resampled['value'].isna()
    outdoor_is_interpolated = outdoor_data_resampled['value'].isna()

    # Interpolate to fill gaps
    indoor_data_resampled = indoor_data_resampled.interpolate()
    outdoor_data_resampled = outdoor_data_resampled.interpolate()

    # Reset index to get timestamps back as a column
    indoor_data_resampled = indoor_data_resampled.reset_index()
    outdoor_data_resampled = outdoor_data_resampled.reset_index()

    # Shift outdoor data by 50 minutes
    outdoor_data_resampled['created_at'] += timedelta(minutes=50)

    # Merge data
    merged_data = pd.merge(outdoor_data_resampled, indoor_data_resampled, on='created_at', suffixes=('_outdoor', '_indoor'))
    merged_data['delta'] = merged_data['value_indoor'] - merged_data['value_outdoor']

    # Combine interpolation flags for merged data
    is_interpolated_indoor = pd.merge(
        outdoor_is_interpolated.reset_index(),
        indoor_is_interpolated.reset_index(),
        on='created_at',
        suffixes=('_outdoor', '_indoor')
    )['value_indoor']
    is_interpolated_outdoor = pd.merge(
        outdoor_is_interpolated.reset_index(),
        indoor_is_interpolated.reset_index(),
        on='created_at',
        suffixes=('_outdoor', '_indoor')
    )['value_outdoor']

    # Prepare metadata about gaps
    total_points = len(merged_data)
    gap_metadata = {
        'indoor_gaps': int(indoor_gaps),
        'outdoor_gaps': int(outdoor_gaps),
        'gap_percentage': (indoor_gaps + outdoor_gaps) / (2 * total_points) * 100
    }

    # Optionally, compute gap periods (start/end times of gaps)
    def find_gap_periods(is_interpolated_series, timestamps):
        gap_periods = []
        in_gap = False
        start_time = None
        for i, (is_gap, timestamp) in enumerate(zip(is_interpolated_series, timestamps)):
            if is_gap and not in_gap:
                in_gap = True
                start_time = timestamp
            elif not is_gap and in_gap:
                in_gap = False
                gap_periods.append({
                    'start': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'end': timestamps[i-1].strftime('%Y-%m-%d %H:%M:%S'),
                    'duration_minutes': int((timestamps[i-1] - start_time).total_seconds() / 60)
                })
        if in_gap:  # Handle case where gap extends to the end
            gap_periods.append({
                'start': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'end': timestamps[-1].strftime('%Y-%m-%d %H:%M:%S'),
                'duration_minutes': int((timestamps[-1] - start_time).total_seconds() / 60)
            })
        return gap_periods

    indoor_gap_periods = find_gap_periods(is_interpolated_indoor, merged_data['created_at'])
    outdoor_gap_periods = find_gap_periods(is_interpolated_outdoor, merged_data['created_at'])

    gap_metadata['indoor_gap_periods'] = indoor_gap_periods
    gap_metadata['outdoor_gap_periods'] = outdoor_gap_periods

    return merged_data, gap_metadata, is_interpolated_indoor.tolist(), is_interpolated_outdoor.tolist()

@app.route('/api/data/<string:location>/<string:sensor_type>/<string:indoor_or_outdoor>/<string:sensor_name>')
def get_single_sensor_data(location, sensor_type, indoor_or_outdoor, sensor_name):
    if location not in locations:
        return jsonify({'error': 'Invalid location'}), 400
    if sensor_type not in fields:
        return jsonify({'error': 'Invalid sensor type'}), 400
    if indoor_or_outdoor not in ['indoor', 'outdoor']:
        return jsonify({'error': 'Invalid sensor specifier, choose "indoor" or "outdoor"'}), 400

    channel_id = locations[location][indoor_or_outdoor].get(sensor_name)
    if channel_id is None:
        return jsonify({'error': f'Sensor {sensor_name} not found for {location} {indoor_or_outdoor}'}), 404

    field = fields[sensor_type]
    data = fetch_data_from_thingspeak(channel_id, field)

    date_range = request.args.get('range', '7d')
    start_date, end_date = parse_date_range(date_range)

    data = data[(data['created_at'] >= start_date) & (data['created_at'] <= end_date)]

    return jsonify({
        'timestamps': data['created_at'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist(),
        'values': data['value'].tolist()
    })

@app.route('/api/delta/<string:location>/<string:sensor_type>')
def get_delta(location, sensor_type):
    if location not in locations:
        return jsonify({'error': 'Invalid location'}), 400
    if sensor_type not in fields:
        return jsonify({'error': 'Invalid sensor type'}), 400

    indoor_sensor_name = request.args.get('indoor_sensor')
    outdoor_sensor_name = request.args.get('outdoor_sensor')

    if not indoor_sensor_name or not outdoor_sensor_name:
        return jsonify({'error': 'Please specify indoor_sensor and outdoor_sensor'}), 400

    field = fields[sensor_type]

    try:
        merged_data, gap_metadata, is_interpolated_indoor, is_interpolated_outdoor = compute_delta(location, field, indoor_sensor_name, outdoor_sensor_name)
    except ValueError as e:
        return jsonify({'error': str(e)}), 404

    date_range = request.args.get('range', '7d')
    start_date, end_date = parse_date_range(date_range)

    merged_data = merged_data[(merged_data['created_at'] >= start_date) & (merged_data['created_at'] <= end_date)]

    return jsonify({
        'timestamps': merged_data['created_at'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist(),
        'indoor_value': merged_data['value_indoor'].tolist(),
        'outdoor_value': merged_data['value_outdoor'].tolist(),
        'values': merged_data['delta'].tolist(),
        'gap_metadata': gap_metadata,
        'is_interpolated_indoor': is_interpolated_indoor,  # New field
        'is_interpolated_outdoor': is_interpolated_outdoor  # New field
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)