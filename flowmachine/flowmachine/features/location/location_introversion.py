# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# -*- coding: utf-8 -*-

from typing import List

"""
Location introversion [1]_ calculates the proportion
of interactions made within a certain location 
in which the interaction counterpart is located
in the same location. Its opposite is
measured by location extroversion.


References
---------
.. [1] Christopher Smith, Afra Mashhadi, Licia Capra. "Ubiquitous Sensing for Mapping Poverty in Developing Countries". NetMob Conference Proceedings, 2013. http://haig.cs.ucl.ac.uk/staff/L.Capra/publicatiONs/d4d.pdf

"""
from ...core import Query
from ...core.mixins import GeoDataMixin


from ...core import location_joined_query, make_spatial_unit
from ..utilities import EventsTablesUnion


class LocationIntroversion(GeoDataMixin, Query):
    """
    Calculates the proportions of events that take place
    within a location in which all involved parties
    are located in the same location (introversion), and those
    which are between parties in different locations (extroversion).

    Parameters
    ----------
    start : str
        ISO format date string to at which to start the analysis
    stop : str
        AS above for the end of the analysis
    table : str, default 'all'
        Specifies a table of cdr data on which to base the analysis. Table must
        exist in events schema. If 'ALL' then we use all tables specified in
        flowmachine.yml.
    spatial_unit : flowmachine.core.spatial_unit.*SpatialUnit, default cell
        Spatial unit to which subscriber locations will be mapped. See the
        docstring of make_spatial_unit for more information.
    direction : str, default 'both'.
        Determines if query should filter only outgoing
        events ('out'), incoming events ('in'), or both ('both').

    Notes
    -----

    Equation 3 of the original paper states introversion as the ratio of introverted to extroverted events
    but indicates that this will return values in the range [0, 1]. However, the preceding text indicate
    that introversion is the _proportion_ of events which are introverted. We follow the latter here.

    Examples
    --------
    >>> LocationIntroversion("2016-01-01", "2016-01-07").head()
          location_id  introversion  extroversion
    0    AUQZGMW3      0.050000      0.950000
    1    ns6vzdkC      0.049180      0.950820
    2    llTlNC7E      0.046122      0.953878
    3    WET2L101      0.045549      0.954451
    4    eAwMUT94      0.045175      0.954825
    """

    def __init__(
        self,
        start,
        stop,
        *,
        table="all",
        spatial_unit=make_spatial_unit("cell"),
        direction="both",
        hours="all",
        subscriber_subset=None,
        subscriber_identifier="msisdn",
    ):
        self.start = start
        self.stop = stop
        self.table = table
        self.spatial_unit = spatial_unit
        self.direction = direction

        self.unioned_query = location_joined_query(
            EventsTablesUnion(
                self.start,
                self.stop,
                columns=["id", "outgoing", "location_id", "datetime"],
                tables=self.table,
                hours=hours,
                subscriber_subset=subscriber_subset,
                subscriber_identifier=subscriber_identifier,
            ),
            spatial_unit=self.spatial_unit,
            time_col="datetime",
        )

        super().__init__()

    @property
    def column_names(self) -> List[str]:
        return self.spatial_unit.location_id_columns + ["introversion", "extroversion"]

    def _make_query(self):
        location_columns = self.spatial_unit.location_id_columns

        if self.direction == "both":
            sql_direction = ""
        elif self.direction == "in":
            sql_direction = """
                WHERE NOT A.outgoing
            """
        elif self.direction == "out":
            sql_direction = """
                WHERE A.outgoing
            """

        sql = f"""
        WITH unioned_table AS ({self.unioned_query.get_query()})
        SELECT *, 1-introversion as extroversion FROM
        (SELECT {', '.join(location_columns)}, sum(introverted::integer)/count(*)::float as introversion FROM (
            SELECT
               {', '.join(f'A.{c} as {c}' for c in location_columns)},
               {' AND '.join(f'A.{c} = B.{c}' for c in location_columns)} as introverted
            FROM unioned_table as A
            INNER JOIN unioned_table AS B
                  ON A.id = B.id
                     AND A.outgoing != B.outgoing
                     {sql_direction}
        ) _
        GROUP BY {', '.join(location_columns)}) _
        ORDER BY introversion DESC
        """

        return sql
