---
title: MongoDB Request Class
parent: Database Classes
nav_order: 3
---

# Todo:
* Review Ada's actual MongoDB setup
* Rewrite this to couple more closely to that setup
* Class Diagram
* Functionality Descriptions
* Functionality Examples

# MongoDB Request Class
We have a MongoDB request class that handles requests to the MongoDB database. This class is used to read data from the MongoDB

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Union

from pymongo import MongoClient, ReadPreference
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.read_concern import ReadConcern


@dataclass
class MongoReaderConfig:
    """Configuration for MongoReader."""
    uri: str                                # e.g. "mongodb+srv://user:pass@cluster.example.mongodb.net"
    database: str                           # database to use by default
    read_preference: ReadPreference = ReadPreference.SECONDARY_PREFERRED
    read_concern: ReadConcern = ReadConcern("majority")
    app_name: str = "MongoReader"
    socket_timeout_ms: Optional[int] = 10_000
    server_selection_timeout_ms: Optional[int] = 10_000
    max_idle_time_ms: Optional[int] = 60_000
    # Limit per-operation time on the server; can be overridden per call
    default_max_time_ms: Optional[int] = 10_000


class MongoReader:
    """
    A read-only MongoDB client focused on fetching data (no writes).

    Notes on safety:
    - This class only exposes read methods and never calls insert/update/delete APIs.
    - For *true* write protection, use a MongoDB user with read-only roles.
    """

    def __init__(self, config: MongoReaderConfig):
        self._config = config
        # retryWrites=False ensures no accidental write retries (reads don't write, but be explicit)
        self._client = MongoClient(
            config.uri,
            appname=config.app_name,
            read_preference=config.read_preference,
            retryWrites=False,
            socketTimeoutMS=config.socket_timeout_ms,
            serverSelectionTimeoutMS=config.server_selection_timeout_ms,
            maxIdleTimeMS=config.max_idle_time_ms,
        )
        self._db: Database = self._client.get_database(
            config.database, read_concern=config.read_concern
        )

    # --- lifecycle ---------------------------------------------------------

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "MongoReader":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # --- helpers -----------------------------------------------------------

    def _coll(self, name: str) -> Collection:
        return self._db.get_collection(name)

    # --- read-only operations ---------------------------------------------

    def ping(self) -> bool:
        """Check connectivity."""
        self._client.admin.command("ping")
        return True

    def list_collections(self) -> List[str]:
        """List collection names in the database."""
        return self._db.list_collection_names()

    def find_one(
        self,
        collection: str,
        filter: Optional[Dict[str, Any]] = None,
        projection: Optional[Dict[str, int]] = None,
        max_time_ms: Optional[int] = None,
        sort: Optional[List[tuple]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Return the first matching document (or None)."""
        kwargs: Dict[str, Any] = {}
        if projection is not None:
            kwargs["projection"] = projection
        if max_time_ms is None:
            max_time_ms = self._config.default_max_time_ms
        if sort is not None:
            kwargs["sort"] = sort
        return self._coll(collection).find_one(
            filter or {}, max_time_ms=max_time_ms, **kwargs
        )

    def find(
        self,
        collection: str,
        filter: Optional[Dict[str, Any]] = None,
        projection: Optional[Dict[str, int]] = None,
        sort: Optional[List[tuple]] = None,
        limit: Optional[int] = None,
        skip: int = 0,
        batch_size: Optional[int] = None,
        max_time_ms: Optional[int] = None,
        allow_disk_use: Optional[bool] = None,
        hint: Optional[Union[str, List[tuple]]] = None,
    ) -> Iterator[Dict[str, Any]]:
        """
        Stream matching documents as an iterator.
        """
        cursor = self._coll(collection).find(
            filter or {},
            projection=projection,
            skip=skip,
            limit=limit or 0,
            sort=sort,
            batch_size=batch_size or 0,
            max_time_ms=max_time_ms or self._config.default_max_time_ms,
            allow_disk_use=allow_disk_use,
            hint=hint,
        )
        for doc in cursor:
            yield doc

    def aggregate(
        self,
        collection: str,
        pipeline: Sequence[Dict[str, Any]],
        allow_disk_use: Optional[bool] = None,
        max_time_ms: Optional[int] = None,
        hint: Optional[Union[str, Dict[str, Any]]] = None,
    ) -> Iterable[Dict[str, Any]]:
        """
        Run a read-only aggregation pipeline.
        (Avoid $out/$merge stages—they write to collections and are not allowed here.)
        """
        # Quick safeguard: reject pipelines containing $out or $merge
        forbidden = {"$out", "$merge"}
        for stage in pipeline:
            if any(op in forbidden for op in stage):
                raise ValueError("Aggregation stages $out/$merge are not permitted.")
        cursor = self._coll(collection).aggregate(
            list(pipeline),
            allowDiskUse=allow_disk_use,
            maxTimeMS=max_time_ms or self._config.default_max_time_ms,
            hint=hint,
        )
        for doc in cursor:
            yield doc

    def distinct(
        self,
        collection: str,
        key: str,
        filter: Optional[Dict[str, Any]] = None,
        max_time_ms: Optional[int] = None,
    ) -> List[Any]:
        """Get distinct values for a field."""
        return self._coll(collection).distinct(
            key,
            filter or {},
            maxTimeMS=max_time_ms or self._config.default_max_time_ms,
        )

    def count(
        self,
        collection: str,
        filter: Optional[Dict[str, Any]] = None,
        max_time_ms: Optional[int] = None,
        hint: Optional[Union[str, List[tuple]]] = None,
        *,
        estimated: bool = False,
    ) -> int:
        """
        Count documents.
        - estimated=True uses collection.estimated_document_count() (fast, approximate).
        - estimated=False uses count_documents(filter) (accurate, uses index/scan).
        """
        if estimated and (filter is None or filter == {}):
            return int(self._coll(collection).estimated_document_count())
        return int(
            self._coll(collection).count_documents(
                filter or {},
                maxTimeMS=max_time_ms or self._config.default_max_time_ms,
                hint=hint,
            )
        )

```