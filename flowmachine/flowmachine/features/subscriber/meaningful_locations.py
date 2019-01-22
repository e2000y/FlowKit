# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from typing import Dict, Any, List, Union

from ...core import GeoTable, Query
from . import LabelEventScore, HartiganCluster, EventScore
from ..spatial import Grid
from ...utils.utils import get_columns_for_level


class MeaningfulLocations(Query):
    """
    Infer 'meaningful' locations for individual subscribers (for example, home and work) based on
    a clustering of the cell towers they use, and their usage patterns for those towers.

    Extension of work by Isaacman et al.[1]_ to scenarios where ground truth data is not available.

    Parameters
    ----------
    clusters : HartiganCluster
        Per subscriber clusters of towers
    scores : EventScore
        Per user, per tower scores based on hour of day and day of week of interactions with the tower
    labels : LabelEventScore
        Labels to apply to clusters given their usage pattern scoring
    label : str
        Meaningful label to extract clusters for

    References
    ----------
    .. [1] S. Isaacman et al., "Identifying Important Places in People's Lives from Cellular Network Data", International Conference on Pervasive Computing (2011), pp 133-151.
    """

    def __init__(
        self,
        *,
        clusters: HartiganCluster,
        scores: EventScore,
        labels: Dict[str, Dict[str, Any]],
        label: str,
    ) -> None:
        labelled_clusters = LabelEventScore(
            scores=clusters.join_to_cluster_components(scores), labels=labels
        )
        self.subset = labelled_clusters.subset("label", label)

        super().__init__()

    @property
    def column_names(self) -> List[str]:
        return ["subscriber", "label", "cluster", "n_clusters"]

    def _make_query(self):
        return f"""
        SELECT subscriber, label, cluster, (sum(1) OVER (PARTITION BY subscriber)) as n_clusters FROM 
            ({self.subset.get_query()}) clus 
        GROUP BY subscriber, label, cluster
        ORDER BY subscriber
        """

    def aggregate(
        self,
        level="admin3",
        column_name=None,
        polygon_table=None,
        geom_column="geom",
        size=None,
    ) -> "MeaningfulLocationsAggregate":
        return MeaningfulLocationsAggregate(
            meaningful_locations=self,
            level=level,
            column_name=column_name,
            polygon_table=polygon_table,
            geom_column=geom_column,
            size=size,
        )


class MeaningfulLocationsAggregate(Query):
    """
    Aggregates an individual level meaningful location to a spatial unit by assigning
    subscribers with clusters in that unit to it. For subscribers with more than one cluster,
    assigns `1/n_clusters` to each spatial unit that the cluster lies in.

    Parameters
    ----------
    meaningful_locations : MeaningfulLocations
        A per-subscriber meaningful locations object to aggregate
    level : {"admin3", "admin2", "admin1", "grid", "polygon"}, default "admin3"
        Spatial unit to aggregate to
    column_name : str or list of str, default None
        Optionally specify a non-default column name or names from the spatial unit table
    polygon_table : str, default None
        When using the "polygon" level, you must specify the fully qualified name of a table
        containing polygons.
    geom_column : str, default "geom"
        When using the "polygon" level, you must specify the name of column containing geometry
    size : int, default None
        When using the "grid" level, you must specify the size of the grid to use in KM
    """

    allowed_levels = {"admin3", "admin2", "admin1", "grid", "polygon"}

    def __init__(
        self,
        *,
        meaningful_locations: MeaningfulLocations,
        level: str = "admin3",
        column_name: Union[str, None, List[str]] = None,
        polygon_table: str = None,
        geom_column: str = "geom",
        size: int = None,
    ) -> None:
        self.meaningful_locations = meaningful_locations
        level_cols = get_columns_for_level(level, column_name)
        self.column_name = column_name
        if level not in MeaningfulLocationsAggregate.allowed_levels:
            raise ValueError(
                f"'{level}' is not an allowed level for meaningful locations, must be one of {MeaningfulLocationsAggregate.allowed_levels}'"
            )
        self.level = level
        if level.startswith("admin"):
            if level_cols == ["pcod"]:
                level_cols = [f"{level}pcod"]
            self.aggregator = GeoTable(
                f"geography.{level}", geom_column="geom", columns=["geom"] + level_cols
            )
        elif level == "polygon":
            self.aggregator = GeoTable(
                polygon_table,
                geom_column=geom_column,
                columns=[geom_column] + level_cols,
            )
        elif level == "grid":
            self.aggregator = Grid(size=size)

    @property
    def column_names(self) -> List[str]:
        return (
            ["label"] + get_columns_for_level(self.level, self.column_name) + ["total"]
        )

    def _make_query(self):
        agg_query, agg_cols = self.aggregator._geo_augmented_query()
        level_cols = get_columns_for_level(self.level, self.column_name)
        level_cols_aliased = level_cols
        if level_cols == ["pcod"]:
            level_cols_aliased = [f"{self.level}pcod as pcod"]

        level_cols = ", ".join(level_cols)
        level_cols_aliased = ", ".join(level_cols_aliased)
        return f"""
        SELECT label, {level_cols_aliased}, sum(1./n_clusters) as total FROM
        ({self.meaningful_locations.get_query()}) meaningful_locations
        LEFT JOIN 
        ({agg_query}) agg
        ON st_contains(agg.geom::geometry, meaningful_locations.cluster::geometry)
        GROUP BY label, {level_cols}
        HAVING sum(1./n_clusters) > 15
        ORDER BY {level_cols}
        """


class MeaningfulLocationsOD(Query):
    """
    Calculates an OD matrix aggregated to a spatial unit between two individual
    level meaningful locations. For subscribers with more than one cluster of either
    label, counts are weight to `1/(n_clusters_label_a*n_clusters_label_b)`.


    Parameters
    ----------
    meaningful_locations_a, meaningful_locations_a : MeaningfulLocations
        Per-subscriber meaningful locations objects calculate an OD between
    level : {"admin3", "admin2", "admin1", "grid", "polygon"}, default "admin3"
        Spatial unit to aggregate to
    column_name : str or list of str, default None
        Optionally specify a non-default column name or names from the spatial unit table
    polygon_table : str, default None
        When using the "polygon" level, you must specify the fully qualified name of a table
        containing polygons.
    geom_column : str, default "geom"
        When using the "polygon" level, you must specify the name of column containing geometry
    size : int, default None
        When using the "grid" level, you must specify the size of the grid to use in KM
    """

    allowed_levels = {"admin3", "admin2", "admin1", "grid", "polygon"}

    def __init__(
        self,
        *,
        meaningful_locations_a: MeaningfulLocations,
        meaningful_locations_b: MeaningfulLocations,
        level: str = "admin3",
        column_name: Union[str, None, List[str]] = None,
        polygon_table: str = None,
        geom_column: str = "geom",
        size: int = None,
    ) -> None:
        self.flow = meaningful_locations_a.join(
            meaningful_locations_b,
            on_left="subscriber",
            left_append="_from",
            right_append="_to",
        )
        level_cols = get_columns_for_level(level, column_name)
        self.column_name = column_name
        if level not in MeaningfulLocationsOD.allowed_levels:
            raise ValueError(
                f"'{level}' is not an allowed level for meaningful locations, must be one of {MeaningfulLocationsOD.allowed_levels}'"
            )
        self.level = level
        if level.startswith("admin"):
            if level_cols == ["pcod"]:
                level_cols = [f"{level}pcod"]
            self.aggregator = GeoTable(
                f"geography.{level}", geom_column="geom", columns=["geom"] + level_cols
            )
        elif level == "polygon":
            self.aggregator = GeoTable(
                polygon_table,
                geom_column=geom_column,
                columns=[geom_column] + level_cols,
            )
        elif level == "grid":
            self.aggregator = Grid(size=size)

    @property
    def column_names(self) -> List[str]:
        return [
            f"{col}_{direction}"
            for col in ["label"] + get_columns_for_level(self.level, self.column_name)
            for direction in ("from", "to")
        ] + ["total"]

    def _make_query(self):
        agg_query, agg_cols = self.aggregator._geo_augmented_query()
        level_cols = [
            f"{col}_{direction}"
            for col in get_columns_for_level(self.level, self.column_name)
            for direction in ("from", "to")
        ]
        level_cols_aliased = [
            f"{direction}_q.{col} as {col}_{direction}"
            for col in get_columns_for_level(self.level, self.column_name)
            for direction in ("from", "to")
        ]
        if level_cols == ["pcod_from", "pcod_to"]:
            level_cols_aliased = [
                f"from_q.{self.level}pcod as pcod_from",
                f"to_q.{self.level}pcod as pcod_to",
            ]

        level_cols = ", ".join(level_cols)
        level_cols_aliased = ", ".join(level_cols_aliased)
        return f"""
        SELECT label_from, label_to, {level_cols_aliased}, sum(1./(n_clusters_from*n_clusters_to)) as total FROM
        ({self.flow.get_query()}) meaningful_locations
        LEFT JOIN 
        ({agg_query}) from_q
        ON st_contains(from_q.geom::geometry, meaningful_locations.cluster_from::geometry)
        LEFT JOIN 
        ({agg_query}) to_q
        ON st_contains(to_q.geom::geometry, meaningful_locations.cluster_to::geometry)
        GROUP BY label_from, label_to, {level_cols}
        HAVING sum(1./(n_clusters_from*n_clusters_to)) > 15
        ORDER BY {level_cols}
        """
