"""
MongoDB Client for Ada Carbon Monitoring
Provides interface to query users and groups from MongoDB to attribute Prometheus usage data
"""
from datetime import datetime
from typing import Optional, Dict, List, Any
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database


class MongoDBClient:
    """
    MongoDB Client for querying Ada database to attribute usage to Users and Groups.

    By combining and matching timestamps, host, cloud_project_name, machine_name from
    the Prometheus database, we can attribute usage to Users and Groups in MongoDB.

    - Users have hold of a specific host at given times (via workspaces collection)
    - Groups are defined by Cloud project and machine name combinations and will be
      named "{cloud_project_name}_{machine_name}"
    """

    def __init__(
        self,
        mongo_uri: str = "mongodb://localhost:27017/",
        database_name: str = "ada",
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        """
        Initialize MongoDB Client.

        Args:
            mongo_uri: MongoDB connection URI
            database_name: Name of the database to connect to
            username: Optional username for authentication
            password: Optional password for authentication
        """
        self.mongo_uri = mongo_uri
        self.database_name = database_name
        self.username = username
        self.password = password

        # Build connection URI with authentication if provided
        if username and password:
            # Extract protocol and host from URI
            if "://" in mongo_uri:
                protocol, rest = mongo_uri.split("://", 1)
                self.mongo_uri = f"{protocol}://{username}:{password}@{rest}"

        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None
        self._connect()

    def _connect(self) -> None:
        """Establish connection to MongoDB."""
        try:
            self.client = MongoClient(self.mongo_uri)
            self.db = self.client[self.database_name]
            # Test connection
            self.client.admin.command('ping')
            print(f"Successfully connected to MongoDB database: {self.database_name}")
        except Exception as e:
            print(f"Failed to connect to MongoDB: {e}")
            raise

    def close(self) -> None:
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            print("MongoDB connection closed")

    def get_user_by_host_and_time(
        self,
        hostname: str,
        timestamp: datetime
    ) -> Optional[Dict[str, Any]]:
        """
        Find the user who had control of a specific host at a given time.

        This is done by querying the workspaces collection to find which workspace
        was active on the given hostname at the specified timestamp, then retrieving
        the user information.

        Args:
            hostname: The hostname to query
            timestamp: The datetime when the usage occurred

        Returns:
            User document if found, None otherwise
        """
        try:
            workspaces: Collection = self.db["workspaces"]

            # Find workspace that was active on this host at this time
            # A workspace is active if:
            # - hostname matches
            # - created_time <= timestamp
            # - (acquired_time is None OR acquired_time <= timestamp)
            # - (deleted_time is None OR deleted_time > timestamp)

            query = {
                "hostname": hostname,
                "created_time": {"$lte": timestamp}
            }

            # Find all workspaces matching hostname and time constraints
            matching_workspaces = list(workspaces.find(query))

            # Filter by acquired_time and deleted_time
            active_workspace = None
            for ws in matching_workspaces:
                acquired_time = ws.get("acquired_time")
                deleted_time = ws.get("deleted_time")

                # Check if workspace was acquired before or at timestamp
                if acquired_time and acquired_time > timestamp:
                    continue

                # Check if workspace was not yet deleted at timestamp
                if deleted_time and deleted_time <= timestamp:
                    continue

                # Found an active workspace
                active_workspace = ws
                break

            if not active_workspace:
                print(f"No active workspace found for host {hostname} at {timestamp}")
                return None

            # Get the owner (user) of this workspace
            owner = active_workspace.get("owner")
            if not owner:
                print(f"No owner found for workspace {active_workspace.get('_id')}")
                return None

            # Retrieve user information
            users: Collection = self.db["users"]
            user = users.find_one({"platform_name": owner})

            if user:
                print(f"Found user {user.get('platform_name')} for host {hostname} at {timestamp}")
                return user
            else:
                print(f"User {owner} not found in users collection")
                return None

        except Exception as e:
            print(f"Error querying user by host and time: {e}")
            return None

    def get_group_by_cloud_project_and_machine(
        self,
        cloud_project_name: str,
        machine_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find a group based on cloud project name and machine name combination.

        Groups are named "{cloud_project_name}_{machine_name}".

        Args:
            cloud_project_name: Name of the cloud project
            machine_name: Name of the machine

        Returns:
            Group document if found, None otherwise
        """
        try:
            groups: Collection = self.db["groups"]

            # Construct expected group name
            group_name = f"{cloud_project_name}_{machine_name}"

            # Query for the group
            group = groups.find_one({"name": group_name})

            if group:
                print(f"Found group: {group_name}")
                return group
            else:
                print(f"Group not found: {group_name}")
                return None

        except Exception as e:
            print(f"Error querying group: {e}")
            return None

    def get_all_groups_for_cloud_project(
        self,
        cloud_project_name: str
    ) -> List[Dict[str, Any]]:
        """
        Get all groups associated with a specific cloud project.

        Args:
            cloud_project_name: Name of the cloud project

        Returns:
            List of group documents
        """
        try:
            groups: Collection = self.db["groups"]

            # Find all groups with names starting with the cloud project name
            pattern = f"^{cloud_project_name}_"
            matching_groups = list(groups.find({
                "name": {"$regex": pattern}
            }))

            print(f"Found {len(matching_groups)} groups for cloud project {cloud_project_name}")
            return matching_groups

        except Exception as e:
            print(f"Error querying groups for cloud project: {e}")
            return []

    def attribute_usage_to_user(
        self,
        hostname: str,
        timestamp: datetime,
        cpu_usage: float,
        additional_metrics: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Attribute usage metrics to a user based on hostname and timestamp.

        Args:
            hostname: The hostname where usage occurred
            timestamp: When the usage occurred
            cpu_usage: CPU usage in seconds
            additional_metrics: Optional dictionary of additional metrics

        Returns:
            Dictionary containing user info and attributed usage, None if user not found
        """
        user = self.get_user_by_host_and_time(hostname, timestamp)

        if not user:
            return None

        attribution = {
            "user": {
                "platform_name": user.get("platform_name"),
                "name": user.get("name"),
                "email": user.get("email"),
                "uid": user.get("uid")
            },
            "usage": {
                "hostname": hostname,
                "timestamp": timestamp,
                "cpu_usage_seconds": cpu_usage
            }
        }

        if additional_metrics:
            attribution["usage"].update(additional_metrics)

        return attribution

    def attribute_usage_to_group(
        self,
        cloud_project_name: str,
        machine_name: str,
        timestamp: datetime,
        cpu_usage: float,
        additional_metrics: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Attribute usage metrics to a group based on cloud project and machine name.

        Args:
            cloud_project_name: Name of the cloud project
            machine_name: Name of the machine
            timestamp: When the usage occurred
            cpu_usage: CPU usage in seconds
            additional_metrics: Optional dictionary of additional metrics

        Returns:
            Dictionary containing group info and attributed usage, None if group not found
        """
        group = self.get_group_by_cloud_project_and_machine(
            cloud_project_name,
            machine_name
        )

        if not group:
            return None

        attribution = {
            "group": {
                "name": group.get("name"),
                "gid": group.get("gid"),
                "type": group.get("type"),
                "members": group.get("members", [])
            },
            "usage": {
                "cloud_project": cloud_project_name,
                "machine": machine_name,
                "timestamp": timestamp,
                "cpu_usage_seconds": cpu_usage
            }
        }

        if additional_metrics:
            attribution["usage"].update(additional_metrics)

        return attribution

    def get_user_by_platform_name(self, platform_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a user by their platform name.

        Args:
            platform_name: The platform name of the user

        Returns:
            User document if found, None otherwise
        """
        try:
            users: Collection = self.db["users"]
            user = users.find_one({"platform_name": platform_name})

            if user:
                print(f"Found user: {platform_name}")
            else:
                print(f"User not found: {platform_name}")

            return user

        except Exception as e:
            print(f"Error retrieving user: {e}")
            return None

    def get_workspaces_by_hostname(
        self,
        hostname: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all workspaces associated with a hostname, optionally filtered by time range.

        Args:
            hostname: The hostname to query
            start_time: Optional start time filter
            end_time: Optional end time filter

        Returns:
            List of workspace documents
        """
        try:
            workspaces: Collection = self.db["workspaces"]

            query = {"hostname": hostname}

            # Add time range filters if provided
            if start_time or end_time:
                time_query = {}
                if start_time:
                    time_query["$gte"] = start_time
                if end_time:
                    time_query["$lte"] = end_time

                if time_query:
                    query["created_time"] = time_query

            workspace_list = list(workspaces.find(query))
            print(f"Found {len(workspace_list)} workspaces for hostname {hostname}")

            return workspace_list

        except Exception as e:
            print(f"Error querying workspaces: {e}")
            return []


# Example Usage
if __name__ == "__main__":
    # Initialize client
    client = MongoDBClient(
        mongo_uri="mongodb://localhost:27017/",
        database_name="ada",
        username=None,  # Set if authentication is required
        password=None   # Set if authentication is required
    )

    try:
        # Example 1: Find user by host and time
        print("\n=== Example 1: Find user by host and time ===")
        user = client.get_user_by_host_and_time(
            hostname="172.16.100.50",
            timestamp=datetime(2025, 9, 23, 17, 0, 0)
        )
        if user:
            print(f"User: {user.get('platform_name')} ({user.get('name')})")

        # Example 2: Find group by cloud project and machine
        print("\n=== Example 2: Find group by cloud project and machine ===")
        group = client.get_group_by_cloud_project_and_machine(
            cloud_project_name="CDAaaS",
            machine_name="MUON"
        )
        if group:
            print(f"Group: {group.get('name')} (GID: {group.get('gid')})")

        # Example 3: Attribute usage to user
        print("\n=== Example 3: Attribute CPU usage to user ===")
        attribution = client.attribute_usage_to_user(
            hostname="172.16.100.50",
            timestamp=datetime(2025, 9, 23, 17, 0, 0),
            cpu_usage=3600.0,  # CPU seconds
            additional_metrics={
                "memory_usage_mb": 8192,
                "carbon_intensity": 45.2
            }
        )
        if attribution:
            print(f"Attributed to user: {attribution['user']['platform_name']}")
            print(f"CPU usage: {attribution['usage']['cpu_usage_seconds']} seconds")

        # Example 4: Attribute usage to group
        print("\n=== Example 4: Attribute CPU usage to group ===")
        attribution = client.attribute_usage_to_group(
            cloud_project_name="CDAaaS",
            machine_name="MUON",
            timestamp=datetime(2025, 9, 23, 17, 0, 0),
            cpu_usage=7200.0,
            additional_metrics={
                "memory_usage_mb": 16384,
                "carbon_intensity": 45.2
            }
        )
        if attribution:
            print(f"Attributed to group: {attribution['group']['name']}")
            print(f"CPU usage: {attribution['usage']['cpu_usage_seconds']} seconds")

    finally:
        # Always close the connection
        client.close()
