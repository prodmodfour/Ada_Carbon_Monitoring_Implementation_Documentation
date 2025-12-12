"""
Workspace Tracker
Integrates MongoDB, Prometheus, and Carbon Intensity APIs to track workspace usage
"""
import sys
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import json

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mongodb.MongoDBClient import MongoDBClient
from prometheus.PrometheusAPIClient import PrometheusAPIClient
from usage_calculation.CarbonIntensityAPIClient import CarbonIntensityAPIClient
from usage_calculation.usage_calculation_functions import (
    estimate_electricity_usage_kwh,
    estimate_carbon_footprint_gCO2eq
)
from workspace_tracking.WorkspaceUsageEntry import WorkspaceUsageEntry
from workspace_tracking.CarbonEquivalencyCalculator import CarbonEquivalencyCalculator


class WorkspaceTracker:
    """
    Track workspace usage across MongoDB, Prometheus, and Carbon Intensity APIs.

    Features:
    - Find all active workspaces from MongoDB
    - Attribute workspaces to users
    - Get CPU usage from Prometheus for current workspace uptime
    - Calculate energy (kWh) and carbon emissions (gCO2eq)
    - Compute carbon equivalencies
    - Store and retrieve usage data
    """

    def __init__(
        self,
        mongo_uri: str = "mongodb://localhost:27017/",
        mongo_db: str = "ada",
        mongo_user: Optional[str] = None,
        mongo_pass: Optional[str] = None,
        prometheus_url: str = "https://host-172-16-100-248.nubes.stfc.ac.uk/",
        default_cpu_tdp_w: float = 100.0
    ):
        """
        Initialize Workspace Tracker.

        Args:
            mongo_uri: MongoDB connection URI
            mongo_db: MongoDB database name
            mongo_user: MongoDB username (optional)
            mongo_pass: MongoDB password (optional)
            prometheus_url: Prometheus server URL
            default_cpu_tdp_w: Default CPU TDP in watts
        """
        # Initialize clients
        self.mongo_client = MongoDBClient(
            mongo_uri=mongo_uri,
            database_name=mongo_db,
            username=mongo_user,
            password=mongo_pass
        )

        self.prometheus_client = PrometheusAPIClient(
            prometheus_url=prometheus_url
        )

        self.carbon_client = CarbonIntensityAPIClient()

        self.equivalency_calc = CarbonEquivalencyCalculator()

        # Configuration
        self.default_cpu_tdp_w = default_cpu_tdp_w

        # Storage for tracked workspaces
        self.tracked_workspaces: Dict[str, WorkspaceUsageEntry] = {}

    def get_active_workspaces(
        self,
        timestamp: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all active workspaces from MongoDB.

        A workspace is considered active if:
        - It has been created
        - It has been acquired by a user
        - It has not been deleted

        Args:
            timestamp: Optional timestamp to check (defaults to now)

        Returns:
            List of active workspace documents
        """
        if timestamp is None:
            timestamp = datetime.now()

        # Query MongoDB for workspaces
        # Active workspaces have state in: READY, CLAIMED
        # And deleted_time is None or in the future
        try:
            workspaces_collection = self.mongo_client.db["workspaces"]

            query = {
                "state": {"$in": ["READY", "CLAIMED"]},
                "$or": [
                    {"deleted_time": None},
                    {"deleted_time": {"$gt": timestamp}}
                ]
            }

            active_workspaces = list(workspaces_collection.find(query))
            print(f"Found {len(active_workspaces)} active workspaces")

            return active_workspaces

        except Exception as e:
            print(f"Error fetching active workspaces: {e}")
            return []

    def track_workspace(
        self,
        workspace: Dict[str, Any],
        timestamp: Optional[datetime] = None,
        cloud_project_name: Optional[str] = None,
        machine_name: Optional[str] = None
    ) -> Optional[WorkspaceUsageEntry]:
        """
        Track a single workspace's usage.

        Args:
            workspace: Workspace document from MongoDB
            timestamp: Timestamp for tracking (defaults to now)
            cloud_project_name: Cloud project name for Prometheus query
            machine_name: Machine name for Prometheus query

        Returns:
            WorkspaceUsageEntry with complete usage data, or None on error
        """
        if timestamp is None:
            timestamp = datetime.now()

        workspace_id = str(workspace.get("_id"))
        hostname = workspace.get("hostname")
        owner = workspace.get("owner")

        if not hostname:
            print(f"Workspace {workspace_id} has no hostname")
            return None

        print(f"\n=== Tracking workspace {workspace_id} ({hostname}) ===")

        # Create usage entry
        entry = WorkspaceUsageEntry(
            workspace_id=workspace_id,
            hostname=hostname,
            owner=owner
        )
        entry.set_timestamp(timestamp)
        entry.set_cpu_tdp(self.default_cpu_tdp_w)

        # Get user information
        if owner:
            user = self.mongo_client.get_user_by_platform_name(owner)
            if user:
                entry.set_user_info({
                    "platform_name": user.get("platform_name"),
                    "name": user.get("name"),
                    "email": user.get("email"),
                    "uid": user.get("uid")
                })

        # Get CPU usage from Prometheus
        if cloud_project_name and machine_name:
            cpu_data = self._get_cpu_usage_from_prometheus(
                hostname=hostname,
                timestamp=timestamp,
                cloud_project_name=cloud_project_name,
                machine_name=machine_name
            )

            if cpu_data:
                entry.set_cpu_seconds_total(
                    cpu_data["busy"],
                    cpu_data["idle"]
                )

                # Calculate energy usage
                busy_kwh = estimate_electricity_usage_kwh(
                    cpu_data["busy"],
                    self.default_cpu_tdp_w
                )
                idle_kwh = estimate_electricity_usage_kwh(
                    cpu_data["idle"],
                    self.default_cpu_tdp_w
                )
                entry.set_usage_kwh(busy_kwh, idle_kwh)

                # Get carbon intensity and calculate emissions
                carbon_intensity = self.carbon_client.get_carbon_intensity(timestamp)
                if carbon_intensity:
                    busy_gco2eq = estimate_carbon_footprint_gCO2eq(
                        busy_kwh,
                        carbon_intensity
                    )
                    idle_gco2eq = estimate_carbon_footprint_gCO2eq(
                        idle_kwh,
                        carbon_intensity
                    )
                    entry.set_usage_gco2eq(
                        busy_gco2eq,
                        idle_gco2eq,
                        carbon_intensity
                    )

                    # Calculate equivalencies
                    total_gco2eq = busy_gco2eq + idle_gco2eq
                    equivalencies = self.equivalency_calc.get_top_equivalencies(
                        total_gco2eq,
                        count=5
                    )
                    entry.set_carbon_equivalencies(equivalencies)

        # Store in tracked workspaces
        self.tracked_workspaces[workspace_id] = entry

        print(f"✓ Tracked workspace {workspace_id}: Status = {entry.status}")
        return entry

    def _get_cpu_usage_from_prometheus(
        self,
        hostname: str,
        timestamp: datetime,
        cloud_project_name: str,
        machine_name: str
    ) -> Optional[Dict[str, float]]:
        """
        Get CPU usage (busy and idle) from Prometheus.

        Args:
            hostname: The hostname to query
            timestamp: Timestamp for the query
            cloud_project_name: Cloud project name
            machine_name: Machine name

        Returns:
            Dictionary with 'busy' and 'idle' CPU seconds, or None on error
        """
        try:
            # Query Prometheus for CPU seconds total
            result = self.prometheus_client.cpu_seconds_total(
                timestamp=timestamp,
                cloud_project_name=cloud_project_name,
                machine_name=machine_name,
                host=hostname
            )

            if not result or result.get("status") != "success":
                print(f"Failed to get CPU data from Prometheus for {hostname}")
                return None

            # Parse Prometheus response
            # Result structure: data.result[].values[]
            data = result.get("data", {})
            results = data.get("result", [])

            if not results:
                print(f"No CPU data found for {hostname}")
                return None

            # Sum up CPU usage across all cores
            # Separate by mode: 'idle' vs non-idle (busy)
            total_busy = 0.0
            total_idle = 0.0

            for series in results:
                metric = series.get("metric", {})
                mode = metric.get("mode", "")
                values = series.get("values", [])

                if not values:
                    continue

                # Get the latest value
                cpu_seconds = float(values[-1][1])

                if mode == "idle":
                    total_idle += cpu_seconds
                else:
                    total_busy += cpu_seconds

            print(f"CPU Usage - Busy: {total_busy:.2f}s, Idle: {total_idle:.2f}s")

            return {
                "busy": total_busy,
                "idle": total_idle
            }

        except Exception as e:
            print(f"Error getting CPU usage from Prometheus: {e}")
            return None

    def track_all_active_workspaces(
        self,
        timestamp: Optional[datetime] = None,
        cloud_project_name: Optional[str] = None,
        machine_name: Optional[str] = None
    ) -> List[WorkspaceUsageEntry]:
        """
        Track all active workspaces.

        Args:
            timestamp: Timestamp for tracking (defaults to now)
            cloud_project_name: Cloud project name for Prometheus queries
            machine_name: Machine name for Prometheus queries

        Returns:
            List of WorkspaceUsageEntry objects
        """
        if timestamp is None:
            timestamp = datetime.now()

        print(f"\n=== Tracking all active workspaces at {timestamp} ===")

        active_workspaces = self.get_active_workspaces(timestamp)
        tracked = []

        for workspace in active_workspaces:
            entry = self.track_workspace(
                workspace=workspace,
                timestamp=timestamp,
                cloud_project_name=cloud_project_name,
                machine_name=machine_name
            )

            if entry:
                tracked.append(entry)

        print(f"\n✓ Successfully tracked {len(tracked)} workspaces")
        return tracked

    def get_workspace_entry(
        self,
        workspace_id: str
    ) -> Optional[WorkspaceUsageEntry]:
        """Get a tracked workspace entry by ID."""
        return self.tracked_workspaces.get(workspace_id)

    def get_all_entries(self) -> List[WorkspaceUsageEntry]:
        """Get all tracked workspace entries."""
        return list(self.tracked_workspaces.values())

    def export_to_json(
        self,
        filepath: str,
        pretty: bool = True
    ) -> None:
        """
        Export all tracked workspaces to JSON file.

        Args:
            filepath: Path to output JSON file
            pretty: Whether to pretty-print JSON
        """
        data = {
            "timestamp": datetime.now().isoformat(),
            "workspace_count": len(self.tracked_workspaces),
            "workspaces": [
                entry.to_dict()
                for entry in self.tracked_workspaces.values()
            ]
        }

        with open(filepath, 'w') as f:
            if pretty:
                json.dump(data, f, indent=2)
            else:
                json.dump(data, f)

        print(f"✓ Exported {len(self.tracked_workspaces)} workspaces to {filepath}")

    def get_summary_statistics(self) -> Dict[str, Any]:
        """
        Get summary statistics for all tracked workspaces.

        Returns:
            Dictionary with aggregated statistics
        """
        if not self.tracked_workspaces:
            return {
                "workspace_count": 0,
                "total_cpu_seconds": 0,
                "total_energy_kwh": 0,
                "total_carbon_gco2eq": 0
            }

        total_cpu_busy = 0.0
        total_cpu_idle = 0.0
        total_energy = 0.0
        total_carbon = 0.0
        complete_count = 0

        for entry in self.tracked_workspaces.values():
            if entry.status == "complete":
                complete_count += 1

                if entry.busy_cpu_seconds_total:
                    total_cpu_busy += entry.busy_cpu_seconds_total
                if entry.idle_cpu_seconds_total:
                    total_cpu_idle += entry.idle_cpu_seconds_total
                if entry.total_usage_kwh:
                    total_energy += entry.total_usage_kwh
                if entry.total_usage_gco2eq:
                    total_carbon += entry.total_usage_gco2eq

        # Calculate equivalencies for total carbon
        total_equivalencies = None
        if total_carbon > 0:
            total_equivalencies = self.equivalency_calc.get_top_equivalencies(
                total_carbon,
                count=5
            )

        return {
            "workspace_count": len(self.tracked_workspaces),
            "complete_count": complete_count,
            "total_cpu_seconds": {
                "busy": total_cpu_busy,
                "idle": total_cpu_idle,
                "total": total_cpu_busy + total_cpu_idle
            },
            "total_energy_kwh": total_energy,
            "total_carbon_gco2eq": total_carbon,
            "carbon_equivalencies": total_equivalencies
        }

    def close(self) -> None:
        """Close all client connections."""
        self.mongo_client.close()
        print("✓ Workspace Tracker closed")


# Example Usage
if __name__ == "__main__":
    print("=== Workspace Tracker Example ===\n")

    # Initialize tracker
    tracker = WorkspaceTracker(
        mongo_uri="mongodb://localhost:27017/",
        mongo_db="ada",
        prometheus_url="https://host-172-16-100-248.nubes.stfc.ac.uk/",
        default_cpu_tdp_w=100.0
    )

    try:
        # Track all active workspaces
        timestamp = datetime(2025, 9, 23, 17, 0, 0)

        tracked = tracker.track_all_active_workspaces(
            timestamp=timestamp,
            cloud_project_name="CDAaaS",
            machine_name="MUON"
        )

        print(f"\n=== Tracked {len(tracked)} Workspaces ===")

        # Get summary statistics
        summary = tracker.get_summary_statistics()
        print(f"\nSummary Statistics:")
        print(f"  Total Workspaces: {summary['workspace_count']}")
        print(f"  Complete: {summary['complete_count']}")
        print(f"  Total CPU (busy): {summary['total_cpu_seconds']['busy']:.2f}s")
        print(f"  Total CPU (idle): {summary['total_cpu_seconds']['idle']:.2f}s")
        print(f"  Total Energy: {summary['total_energy_kwh']:.2f} kWh")
        print(f"  Total Carbon: {summary['total_carbon_gco2eq']:.2f} gCO2eq")

        if summary['carbon_equivalencies']:
            print(f"\nTop Carbon Equivalencies:")
            for key, equiv in summary['carbon_equivalencies']['top_equivalencies'].items():
                calc = tracker.equivalency_calc
                print(f"  - {calc.format_equivalency(equiv)}")

        # Export to JSON
        # tracker.export_to_json("/tmp/workspace_usage.json")

        # Print individual workspace details
        print(f"\n=== Individual Workspace Details ===")
        for entry in tracker.get_all_entries()[:3]:  # Show first 3
            print(f"\nWorkspace: {entry.workspace_id}")
            print(f"  Hostname: {entry.hostname}")
            print(f"  Owner: {entry.owner}")
            print(f"  Status: {entry.status}")
            if entry.total_usage_gco2eq:
                print(f"  Carbon: {entry.total_usage_gco2eq:.2f} gCO2eq")

    finally:
        tracker.close()
