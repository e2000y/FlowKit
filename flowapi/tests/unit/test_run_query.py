# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest

from flowapi.zmq_helpers import ZMQReply


@pytest.mark.asyncio
async def test_post_query(app, dummy_zmq_server, access_token_builder):
    """
    Test that correct status of 202 & redirect is returned when sending a query.
    """
    client, db, log_dir, app = app

    token = access_token_builder({"daily_location": {"permissions": {"run": True}}})
    dummy_zmq_server.return_value = ZMQReply(
        status="success", payload={"query_id": "DUMMY_QUERY_ID"}
    ).as_json()
    response = await client.post(
        f"/api/0/run",
        headers={"Authorization": f"Bearer {token}"},
        json={"query_kind": "daily_location", "params": {"date": "2016-01-01"}},
    )
    assert response.status_code == 202
    assert "/api/0/poll/DUMMY_QUERY_ID" == response.headers["Location"]


@pytest.mark.parametrize(
    "query, expected_msg",
    [
        (
            {"query_kind": "daily_location", "params": {"date": "2016-01-01"}},
            "Broken query",
        ),
        (
            {"params": {"date": "2016-01-01"}},
            "Query kind must be specified when running a query.",
        ),
    ],
)
@pytest.mark.asyncio
async def test_post_query_error(
    query, expected_msg, app, dummy_zmq_server, access_token_builder
):
    """
    Test that correct status of 403 is returned for a broken query.
    """
    client, db, log_dir, app = app

    token = access_token_builder({"daily_location": {"permissions": {"run": True}}})
    dummy_zmq_server.return_value = ZMQReply(
        status="error", msg="Broken query"
    ).as_json()
    response = await client.post(
        f"/api/0/run", headers={"Authorization": f"Bearer {token}"}, json=query
    )
    json = await response.get_json()
    assert response.status_code == 400
    assert expected_msg == json["msg"]
