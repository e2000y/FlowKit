# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import pytest

from flowmachine.features import (
    HartiganCluster,
    CallDays,
    subscriber_locations,
    EventScore,
)
from flowmachine.features.subscriber.meaningful_locations import (
    MeaningfulLocations,
    MeaningfulLocationsAggregate,
    MeaningfulLocationsOD,
)

labels = {
    "evening": {
        "type": "Polygon",
        "coordinates": [[[1e-06, -0.5], [1e-06, -1.1], [1.1, -1.1], [1.1, -0.5]]],
    },
    "day": {
        "type": "Polygon",
        "coordinates": [[[-1.1, -0.5], [-1.1, 0.5], [-1e-06, 0.5], [0, -0.5]]],
    },
}


def test_column_names_meaningful_locations(get_column_names_from_run):
    """ Test that column_names property matches head(0) for meaningfullocations"""
    mfl = MeaningfulLocations(
        clusters=HartiganCluster(
            calldays=CallDays(
                subscriber_locations=subscriber_locations(
                    start="2016-01-01", stop="2016-01-02", level="versioned-site"
                )
            ),
            radius=1,
        ),
        scores=EventScore(
            start="2016-01-01", stop="2016-01-02", level="versioned-site"
        ),
        labels=labels,
        label="evening",
    )

    assert get_column_names_from_run(mfl) == mfl.column_names


def test_column_names_meaningful_locations_aggregate(
    exemplar_level_param, get_column_names_from_run
):
    """ Test that column_names property matches head(0) for aggregated meaningful locations"""
    if exemplar_level_param["level"] not in MeaningfulLocationsAggregate.allowed_levels:
        pytest.xfail(
            f'The level "{exemplar_level_param["level"]}" is not supported as an aggregation unit for MeaningfulLocations.'
        )
    mfl_agg = MeaningfulLocations(
        clusters=HartiganCluster(
            calldays=CallDays(
                subscriber_locations=subscriber_locations(
                    start="2016-01-01", stop="2016-01-02", level="versioned-site"
                )
            ),
            radius=1,
        ),
        scores=EventScore(
            start="2016-01-01", stop="2016-01-02", level="versioned-site"
        ),
        labels=labels,
        label="evening",
    ).aggregate(**exemplar_level_param)

    assert get_column_names_from_run(mfl_agg) == mfl_agg.column_names


def test_meaningful_locations_aggregate_disallowed_level_raises():
    """ Test that a bad level raises a ValueError"""

    with pytest.raises(ValueError):
        mfl_agg = MeaningfulLocations(
            clusters=HartiganCluster(
                calldays=CallDays(
                    subscriber_locations=subscriber_locations(
                        start="2016-01-01", stop="2016-01-02", level="versioned-site"
                    )
                ),
                radius=1,
            ),
            scores=EventScore(
                start="2016-01-01", stop="2016-01-02", level="versioned-site"
            ),
            labels=labels,
            label="evening",
        ).aggregate(level="NOT_A_LEVEL")


def test_column_names_meaningful_locations_od(
    exemplar_level_param, get_column_names_from_run
):
    """ Test that column_names property matches head(0) for an od matrix between meaningful locations"""
    if exemplar_level_param["level"] not in MeaningfulLocationsAggregate.allowed_levels:
        pytest.xfail(
            f'The level "{exemplar_level_param["level"]}" is not supported as an aggregation unit for ODs between MeaningfulLocations.'
        )
    mfl_a = MeaningfulLocations(
        clusters=HartiganCluster(
            calldays=CallDays(
                subscriber_locations=subscriber_locations(
                    start="2016-01-01", stop="2016-01-02", level="versioned-site"
                )
            ),
            radius=1,
        ),
        scores=EventScore(
            start="2016-01-01", stop="2016-01-02", level="versioned-site"
        ),
        labels=labels,
        label="evening",
    )

    mfl_b = MeaningfulLocations(
        clusters=HartiganCluster(
            calldays=CallDays(
                subscriber_locations=subscriber_locations(
                    start="2016-01-01", stop="2016-01-02", level="versioned-site"
                )
            ),
            radius=1,
        ),
        scores=EventScore(
            start="2016-01-01", stop="2016-01-02", level="versioned-site"
        ),
        labels=labels,
        label="unknown",
    )
    mfl_od = MeaningfulLocationsOD(
        meaningful_locations_a=mfl_a,
        meaningful_locations_b=mfl_b,
        **exemplar_level_param,
    )

    assert get_column_names_from_run(mfl_od) == mfl_od.column_names


@pytest.mark.parametrize(
    "label, expected_number_of_clusters",
    [("evening", 702), ("day", 0), ("unknown", 1615)],
)
def test_meaningful_locations_results(
    label, expected_number_of_clusters, get_dataframe
):
    """
    Test that MeaningfulLocations returns expected results and counts clusters per subscriber correctly.
    """
    mfl = MeaningfulLocations(
        clusters=HartiganCluster(
            calldays=CallDays(
                subscriber_locations=subscriber_locations(
                    start="2016-01-01", stop="2016-01-02", level="versioned-site"
                )
            ),
            radius=1,
        ),
        scores=EventScore(
            start="2016-01-01", stop="2016-01-02", level="versioned-site"
        ),
        labels=labels,
        label=label,
    )
    mfl_df = get_dataframe(mfl)
    assert len(mfl_df) == expected_number_of_clusters
    count_clusters = mfl_df.groupby(
        ["subscriber", "label", "n_clusters"], as_index=False
    ).count()
    # Check that query has correctly counted the number of clusters per subscriber
    assert all(count_clusters.n_clusters == count_clusters.cluster)


def test_meaningful_locations_aggregation_results(exemplar_level_param, get_dataframe):
    """
    Test that MeaningfulLocations returns expected results and counts clusters per subscriber correctly.
    """
    if exemplar_level_param["level"] not in MeaningfulLocationsAggregate.allowed_levels:
        pytest.xfail(
            f'The level "{exemplar_level_param["level"]}" is not supported as an aggregation unit for MeaningfulLocations.'
        )
    mfl = MeaningfulLocations(
        clusters=HartiganCluster(
            calldays=CallDays(
                subscriber_locations=subscriber_locations(
                    start="2016-01-01", stop="2016-01-02", level="versioned-site"
                )
            ),
            radius=1,
        ),
        scores=EventScore(
            start="2016-01-01", stop="2016-01-02", level="versioned-site"
        ),
        labels=labels,
        label="evening",
    )
    mfl_agg = mfl.aggregate(**exemplar_level_param)
    mfl_df = get_dataframe(mfl)
    mfl_agg_df = get_dataframe(mfl_agg)
    # Aggregate should not include any counts below 15
    assert all(mfl_agg_df.total > 15)
    # Sum of aggregate should be less than the number of unique subscribers
    assert mfl_agg_df.total.sum() < mfl_df.subscriber.nunique()


def test_meaningful_locations_aggregation_results(exemplar_level_param, get_dataframe):
    """
    Test that aggregating MeaningfulLocations returns expected results redacts values below 15.
    """
    if exemplar_level_param["level"] not in MeaningfulLocationsAggregate.allowed_levels:
        pytest.xfail(
            f'The level "{exemplar_level_param["level"]}" is not supported as an aggregation unit for MeaningfulLocations.'
        )
    mfl = MeaningfulLocations(
        clusters=HartiganCluster(
            calldays=CallDays(
                subscriber_locations=subscriber_locations(
                    start="2016-01-01", stop="2016-01-02", level="versioned-site"
                )
            ),
            radius=1,
        ),
        scores=EventScore(
            start="2016-01-01", stop="2016-01-02", level="versioned-site"
        ),
        labels=labels,
        label="evening",
    )
    mfl_agg = mfl.aggregate(**exemplar_level_param)
    mfl_df = get_dataframe(mfl)
    mfl_agg_df = get_dataframe(mfl_agg)
    # Aggregate should not include any counts below 15
    assert all(mfl_agg_df.total > 15)
    # Sum of aggregate should be less than the number of unique subscribers
    assert mfl_agg_df.total.sum() < mfl_df.subscriber.nunique()


def test_meaningful_locations_od_raises_for_bad_level(
    exemplar_level_param, get_dataframe
):
    """
    Test that od on meaningful locations raises a ValueError for a bad level.
    """
    mfl = MeaningfulLocations(
        clusters=HartiganCluster(
            calldays=CallDays(
                subscriber_locations=subscriber_locations(
                    start="2016-01-01", stop="2016-01-02", level="versioned-site"
                )
            ),
            radius=1,
        ),
        scores=EventScore(
            start="2016-01-01", stop="2016-01-02", level="versioned-site"
        ),
        labels=labels,
        label="evening",
    )

    with pytest.raises(ValueError):
        mfl_od = MeaningfulLocationsOD(
            meaningful_locations_a=mfl, meaningful_locations_b=mfl, level="NOT_A_LEVEL"
        )
