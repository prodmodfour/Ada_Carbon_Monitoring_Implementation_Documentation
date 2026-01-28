"""
Workspace Usage Entry
Data model for storing workspace usage metrics
"""
import json
from datetime import datetime
from typing import Optional, Dict, Any


class WorkspaceUsageEntry:
    """
    Represents usage metrics for a single workspace at a specific point in time.

    Tracks both busy and idle CPU usage, converts to energy (kWh) and carbon (gCO2eq),
    and includes carbon equivalencies for better understanding.
    """

    def __init__(
        self,
        workspace_id: str,
        hostname: str,
        owner: Optional[str] = None
    ):
        """
        Initialize a workspace usage entry.

        Args:
            workspace_id: MongoDB workspace ID
            hostname: The hostname of the workspace
            owner: Platform name of the workspace owner
        """
        self.workspace_id = workspace_id
        self.hostname = hostname
        self.owner = owner
        self.timestamp: Optional[datetime] = None

        # User information
        self.user_info: Optional[Dict[str, Any]] = None

        # CPU metrics
        self.busy_cpu_seconds_total: Optional[float] = None
        self.idle_cpu_seconds_total: Optional[float] = None

        # Energy metrics (kWh)
        self.busy_usage_kwh: Optional[float] = None
        self.idle_usage_kwh: Optional[float] = None
        self.total_usage_kwh: Optional[float] = None

        # Carbon metrics (gCO2eq)
        self.busy_usage_gco2eq: Optional[float] = None
        self.idle_usage_gco2eq: Optional[float] = None
        self.total_usage_gco2eq: Optional[float] = None

        # Carbon intensity used for calculation
        self.carbon_intensity_g_per_kwh: Optional[float] = None

        # Carbon equivalencies
        self.carbon_equivalencies: Optional[Dict[str, Any]] = None

        # Status tracking
        self.status = "initialized"

        # Machine specifications
        self.cpu_tdp_w: Optional[float] = None  # CPU TDP in watts

    def set_timestamp(self, timestamp: datetime) -> None:
        """Set the timestamp for this entry."""
        self.timestamp = timestamp
        self._update_status()

    def set_user_info(self, user_info: Dict[str, Any]) -> None:
        """Set user information from MongoDB."""
        self.user_info = user_info
        self._update_status()

    def set_cpu_seconds_total(
        self,
        busy_cpu_seconds: float,
        idle_cpu_seconds: float
    ) -> None:
        """Set CPU usage in seconds (busy and idle)."""
        self.busy_cpu_seconds_total = busy_cpu_seconds
        self.idle_cpu_seconds_total = idle_cpu_seconds
        self._update_status()

    def set_usage_kwh(
        self,
        busy_kwh: float,
        idle_kwh: float
    ) -> None:
        """Set energy usage in kWh (busy and idle)."""
        self.busy_usage_kwh = busy_kwh
        self.idle_usage_kwh = idle_kwh
        self.total_usage_kwh = busy_kwh + idle_kwh
        self._update_status()

    def set_usage_gco2eq(
        self,
        busy_gco2eq: float,
        idle_gco2eq: float,
        carbon_intensity: Optional[float] = None
    ) -> None:
        """
        Set carbon emissions in gCO2eq (busy and idle).

        Args:
            busy_gco2eq: Busy mode carbon emissions
            idle_gco2eq: Idle mode carbon emissions
            carbon_intensity: Optional carbon intensity used for calculation
        """
        self.busy_usage_gco2eq = busy_gco2eq
        self.idle_usage_gco2eq = idle_gco2eq
        self.total_usage_gco2eq = busy_gco2eq + idle_gco2eq

        if carbon_intensity is not None:
            self.carbon_intensity_g_per_kwh = carbon_intensity

        self._update_status()

    def set_carbon_equivalencies(self, equivalencies: Dict[str, Any]) -> None:
        """Set carbon equivalencies for better understanding."""
        self.carbon_equivalencies = equivalencies
        self._update_status()

    def set_cpu_tdp(self, cpu_tdp_w: float) -> None:
        """Set CPU TDP in watts."""
        self.cpu_tdp_w = cpu_tdp_w
        self._update_status()

    def _update_status(self) -> None:
        """Update entry status based on available data."""
        has_cpu = (
            self.busy_cpu_seconds_total is not None and
            self.idle_cpu_seconds_total is not None
        )
        has_kwh = (
            self.busy_usage_kwh is not None and
            self.idle_usage_kwh is not None
        )
        has_carbon = (
            self.busy_usage_gco2eq is not None and
            self.idle_usage_gco2eq is not None
        )
        has_user = self.user_info is not None
        has_timestamp = self.timestamp is not None

        if has_cpu and has_kwh and has_carbon and has_user and has_timestamp:
            self.status = "complete"
        elif has_cpu and has_kwh and has_carbon:
            self.status = "processed"
        elif has_cpu:
            self.status = "downloaded"
        else:
            self.status = "initialized"

    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to dictionary."""
        return {
            "workspace_id": self.workspace_id,
            "hostname": self.hostname,
            "owner": self.owner,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "user_info": self.user_info,
            "cpu_usage": {
                "busy_seconds": self.busy_cpu_seconds_total,
                "idle_seconds": self.idle_cpu_seconds_total,
                "total_seconds": (
                    self.busy_cpu_seconds_total + self.idle_cpu_seconds_total
                    if self.busy_cpu_seconds_total and self.idle_cpu_seconds_total
                    else None
                )
            },
            "energy_kwh": {
                "busy": self.busy_usage_kwh,
                "idle": self.idle_usage_kwh,
                "total": self.total_usage_kwh
            },
            "carbon_gco2eq": {
                "busy": self.busy_usage_gco2eq,
                "idle": self.idle_usage_gco2eq,
                "total": self.total_usage_gco2eq
            },
            "carbon_intensity_g_per_kwh": self.carbon_intensity_g_per_kwh,
            "carbon_equivalencies": self.carbon_equivalencies,
            "cpu_tdp_w": self.cpu_tdp_w,
            "status": self.status
        }

    def to_json(self) -> str:
        """Convert entry to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    def __repr__(self) -> str:
        """String representation of the entry."""
        return (
            f"WorkspaceUsageEntry("
            f"workspace_id='{self.workspace_id}', "
            f"hostname='{self.hostname}', "
            f"owner='{self.owner}', "
            f"status='{self.status}')"
        )


# Example Usage
if __name__ == "__main__":
    print("=== Testing WorkspaceUsageEntry ===\n")

    # Create entry
    entry = WorkspaceUsageEntry(
        workspace_id="507f1f77bcf86cd799439011",
        hostname="172.16.100.50",
        owner="john.doe"
    )

    print(f"Initial: {entry}")
    print(f"Status: {entry.status}\n")

    # Set timestamp
    entry.set_timestamp(datetime(2025, 9, 23, 17, 0, 0))
    print(f"After timestamp: Status = {entry.status}")

    # Set user info
    entry.set_user_info({
        "platform_name": "john.doe",
        "name": "John Doe",
        "email": "john.doe@example.com",
        "uid": 1001
    })
    print(f"After user info: Status = {entry.status}")

    # Set CPU usage
    entry.set_cpu_seconds_total(3600.0, 1800.0)
    print(f"After CPU data: Status = {entry.status}")

    # Set energy usage
    entry.set_usage_kwh(2.5, 1.0)
    print(f"After energy data: Status = {entry.status}")

    # Set carbon emissions
    entry.set_usage_gco2eq(112.5, 45.0, carbon_intensity=45.0)
    print(f"After carbon data: Status = {entry.status}")

    # Set equivalencies
    entry.set_carbon_equivalencies({
        "smartphone_charges": 19.15,
        "miles_driven": 0.39
    })
    print(f"After equivalencies: Status = {entry.status}\n")

    # Print full entry as JSON
    print("=== Complete Entry (JSON) ===")
    print(entry.to_json())
