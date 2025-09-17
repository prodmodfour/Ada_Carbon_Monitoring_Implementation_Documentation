from django.core.management.base import BaseCommand
import os
from data.helpers.refresh_project_data import refresh_project_data
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = "Refresh the database with the latest data."

    def handle(self, *args, **kwargs):
        print("Refreshing the database with the latest data.")

    cloud_project_name_labels = ["IDAaaS"]


    start_timestamp = (datetime.now() - timedelta(hours=1))
    end_timestamp = datetime.now()
    print(f"Start timestamp: {start_timestamp}")
    print(f"End timestamp: {end_timestamp}")

    for cloud_project_name in cloud_project_name_labels:
        refresh_project_data(cloud_project_name, start_timestamp, end_timestamp)
        