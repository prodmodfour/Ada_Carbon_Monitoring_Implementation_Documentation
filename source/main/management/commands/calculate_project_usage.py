from django.core.management.base import BaseCommand
import pandas as pd
import numpy as np 
import pyarrow  
import os

class Command(BaseCommand):
    help = "Calculate project usage and estimate electricity consumption."

    def handle(self, *args, **kwargs):
        print("Starting calculation of project electricity usage.")

        INPUT_FILE = "node_cpu_seconds_total.parquet"
        OUTPUT_FILE = "project_estimated_electricity_usage.parquet"
        PROJECT_NAMES = ["CDAaaS", "IDAaaS", "DDAaaS"]
        
        # Power consumption constants (in Watts per core)
        BUSY_WATTAGE = 12  
        IDLE_WATTAGE = 1   
        
        try:
            print(f"Loading data from '{INPUT_FILE}'...")
            df = pd.read_parquet(INPUT_FILE)
            print("Data loaded successfully.")
        except FileNotFoundError:
            print(f"Error: Input file '{INPUT_FILE}' not found. Please run the 'build_database' command first.")
            return
        except Exception as e:
            print(f"An error occurred while reading the Parquet file: {e}")
            return

        # Calculation
        all_projects_usage = []

        for project in PROJECT_NAMES:
            print(f"Processing project: {project}...")
            
            # 1. Filter data for the current project
            project_df = df[df['cloud_project_name'] == project].copy()
            
            if project_df.empty:
                print(f"Warning: No data found for project '{project}'. Skipping.")
                continue

            # 2. Classify usage into 'idle' and 'busy'
            # Create a new column to categorize the seconds based on the 'mode'
            project_df['usage_type'] = np.where(
                project_df['mode'] == 'idle', 
                'idle_seconds', 
                'busy_seconds'
            )

            # 3. Aggregate CPU seconds by timestamp
            # Pivot the table to sum up all 'idle_seconds' and 'busy_seconds' for each unique timestamp.
            # This creates a DataFrame where each row is a timestamp and columns are total seconds for each usage type.
            usage_summary = project_df.pivot_table(
                index='timestamp',
                columns='usage_type',
                values='value',
                aggfunc='sum'
            ).fillna(0) # Replace any NaN values with 0

            # 4. Calculate energy consumption in Watt-Hours
            # Energy (Joules) = Power (Watts) * Time (seconds)
            idle_joules = usage_summary.get('idle_seconds', 0) * IDLE_WATTAGE
            busy_joules = usage_summary.get('busy_seconds', 0) * BUSY_WATTAGE
            
            # Convert total energy from Joules to Watt-Hours (1 Wh = 3600 Joules)
            usage_summary['estimated_watt_hours'] = (idle_joules + busy_joules) / 3600

            # 5. Format the output for this project
            project_result = usage_summary[['estimated_watt_hours']].reset_index()
            project_result['project_name'] = project # Add project name column
            
            all_projects_usage.append(project_result)

        # Save Output
        if not all_projects_usage:
            print("No usage data was processed. Output file will not be created.")
            return
            
        # Combine results from all projects into a single DataFrame
        final_df = pd.concat(all_projects_usage, ignore_index=True)
        
        # Reorder columns for clarity
        final_df = final_df[['project_name', 'timestamp', 'estimated_watt_hours']]

        try:
            print(f"Saving estimated electricity usage to '{OUTPUT_FILE}'...")
            final_df.to_parquet(OUTPUT_FILE, engine='pyarrow')
            print(f"Successfully created '{OUTPUT_FILE}' with {len(final_df)} records.")
        except Exception as e:
            print(f"An error occurred while saving the output file: {e}")