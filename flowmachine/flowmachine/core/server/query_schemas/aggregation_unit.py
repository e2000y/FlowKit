# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from flowmachine.core import make_spatial_unit

from marshmallow.fields import String
from marshmallow.validate import OneOf


class AggregationUnit(String):
    """
    A string representing an aggregation unit (for example: "admin0", "admin1", "admin2", ...)
    """

    def __init__(self, required=True, **kwargs):
        validate = OneOf(["admin0", "admin1", "admin2", "admin3"])
        super().__init__(required=required, validate=validate, **kwargs)


def get_spatial_unit_obj(aggregation_unit_string):
    """
    Given an aggregation unit string (as validated by AggregationUnit()),
    return a FlowMachine spatial unit object.
    """
    if "admin" in aggregation_unit_string:
        level = int(aggregation_unit_string[-1])
        spatial_unit_args = {
            "spatial_unit_type": "admin",
            "level": level,
            "region_id_column_name": [
                f"{aggregation_unit_string}name",
                f"{aggregation_unit_string}pcod",
            ],
        }
    return make_spatial_unit(**spatial_unit_args)
