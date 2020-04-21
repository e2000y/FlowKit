# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from marshmallow import fields, post_load
from marshmallow.validate import OneOf

from flowmachine.features.location.redacted_trips_od_matrix import RedactedTripsODMatrix
from flowmachine.features.utilities.subscriber_locations import SubscriberLocations
from flowmachine.features.location.trips_od_matrix import TripsODMatrix
from .base_exposed_query import BaseExposedQuery
from .base_schema import BaseSchema
from .custom_fields import SubscriberSubset, ISODateTime
from .aggregation_unit import AggregationUnit, get_spatial_unit_obj

__all__ = ["TripsODMatrixSchema", "TripsODMatrixExposed"]


class TripsODMatrixExposed(BaseExposedQuery):
    def __init__(
        self, start_date, end_date, *, aggregation_unit, subscriber_subset=None,
    ):
        # Note: all input parameters need to be defined as attributes on `self`
        # so that marshmallow can serialise the object correctly.
        self.start_date = start_date
        self.end_date = end_date
        self.aggregation_unit = aggregation_unit
        self.subscriber_subset = subscriber_subset

    @property
    def _flowmachine_query_obj(self):
        """
        Return the underlying flowmachine object.

        Returns
        -------
        Query
        """
        return RedactedTripsODMatrix(
            trips=TripsODMatrix(
                SubscriberLocations(
                    self.start_date,
                    self.end_date,
                    spatial_unit=get_spatial_unit_obj(self.aggregation_unit),
                    subscriber_subset=self.subscriber_subset,
                )
            )
        )


class TripsODMatrixSchema(BaseSchema):
    # query_kind parameter is required here for claims validation
    query_kind = fields.String(validate=OneOf(["trips_od_matrix"]))
    start_date = ISODateTime(required=True)
    end_date = ISODateTime(required=True)
    aggregation_unit = AggregationUnit()
    subscriber_subset = SubscriberSubset()

    __model__ = TripsODMatrixExposed
