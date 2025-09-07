from django.core.management.base import BaseCommand
import pandas as pd
import requests
import pyarrow 

class Command(BaseCommand):
    help = "Calculate project carbon footprint using regional carbon intensity data."

    def handle(self, *args, **kwargs):
        print("Starting calculation of project carbon footprint.")

        INPUT_FILE = "project_estimated_electricity_usage.parquet"
        OUTPUT_FILE = "project_carbon_footprint.parquet"
        
        # Carbon Intensity API constants
        # Region ID for South England
        REGION_ID = 12 
        API_BASE_URL = "https://api.carbonintensity.org.uk"

        # Load the pre-calculated electricity usage data
        try:
            print(f"Loading electricity usage data from '{INPUT_FILE}'...")
            df = pd.read_parquet(INPUT_FILE)
            if df.empty:
                print("Warning: Input file is empty. No footprint to calculate.")
                return
            print("Data loaded successfully.")
        except FileNotFoundError:
            print(f"Error: Input file '{INPUT_FILE}' not found. Please run the 'calculate_project_usage' command first.")
            return
        except Exception as e:
            print(f"An error occurred while reading the Parquet file: {e}")
            return

        # Fetch Carbon Intensity Data from API
        print(f"Fetching carbon intensity data for region ID {REGION_ID} (South England)...")
        
        # Ensure timestamp is in datetime format
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Determine the date range needed for the API call, using the min and max timestamps from the usage data
        start_date = df['timestamp'].min().isoformat() + 'Z'
        end_date = df['timestamp'].max().isoformat() + 'Z'
        
        api_url = f"{API_BASE_URL}/regional/intensity/{start_date}/{end_date}/regionid/{REGION_ID}"
        
        try:
            response = requests.get(api_url)
            response.raise_for_status() # Raises an HTTPError for bad responses (4XX or 5XX)
            
            api_data = response.json()
            # The actual intensity data is nested within the response
            intensity_records = api_data['data'][0]['data'] 
            
            if not intensity_records:
                print("Warning: Carbon intensity API returned no data for the specified time range.")
                return

            print(f"Successfully fetched {len(intensity_records)} carbon intensity records.")
            
            # Create a DataFrame from the API data
            intensity_df = pd.DataFrame(intensity_records)
            # Extract the actual intensity value (gCO2/kWh)
            intensity_df['carbon_intensity'] = intensity_df['intensity'].apply(lambda x: x.get('actual', x.get('forecast')))
            intensity_df = intensity_df[['from', 'carbon_intensity']]
            intensity_df.rename(columns={'from': 'intensity_timestamp'}, inplace=True)
            intensity_df['intensity_timestamp'] = pd.to_datetime(intensity_df['intensity_timestamp'])

        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from Carbon Intensity API: {e}")
            return
        except (KeyError, IndexError) as e:
            print(f"Error parsing API response. Unexpected data structure: {e}")
            return

        # Merge usage data with carbon intensity data
        # The API provides data in 30-minute intervals. We match each usage timestamp
        # to its corresponding 30-minute interval start time.
        df['intensity_timestamp'] = df['timestamp'].dt.floor('30T')
        
        # Merge the two dataframes on the aligned timestamp
        merged_df = pd.merge(df, intensity_df, on='intensity_timestamp', how='left')

        # Check for any timestamps that didn't get a match from the API
        missing_intensity = merged_df['carbon_intensity'].isnull().sum()
        if missing_intensity > 0:
            print(f"Warning: Could not find carbon intensity for {missing_intensity} records. These will be excluded from the footprint calculation.")
            merged_df.dropna(subset=['carbon_intensity'], inplace=True)

        # Calculate Carbon Footprint
        # Formula: Footprint (gCO2e) = Energy (kWh) * Intensity (gCO2e/kWh)
        # First, convert Watt-Hours to KiloWatt-Hours
        merged_df['estimated_kwh'] = merged_df['estimated_watt_hours'] / 1000
        
        # Now, calculate the carbon footprint in grams of CO2 equivalent
        merged_df['carbon_footprint_gCO2e'] = merged_df['estimated_kwh'] * merged_df['carbon_intensity']

        # Prepare and save the final output
        final_df = merged_df[['project_name', 'timestamp', 'carbon_footprint_gCO2e']]
        
        try:
            print(f"Saving carbon footprint data to '{OUTPUT_FILE}'...")
            final_df.to_parquet(OUTPUT_FILE, engine='pyarrow')
            print(f"Successfully created '{OUTPUT_FILE}' with {len(final_df)} records.")
        except Exception as e:
            print(f"An error occurred while saving the output file: {e}")