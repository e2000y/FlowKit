# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import json

import pytest
from flowmachine.core.init import _init_logging

from flowmachine.core import Query


@pytest.mark.asyncio
async def test_query_run_logged(json_log):
    # Local import so pytest can capture stdout
    from flowmachine.core.server.server import get_reply_for_message

    msg_contents = {
        "action": "run_query",
        "request_id": "DUMMY_API_REQUEST_ID",
        "params": {"query_kind": "dummy_query", "dummy_param": "DUMMY"},
    }
    _init_logging("ERROR")  # Logging of query runs should be independent of other logs
    Query.redis.get.return_value = (
        b"known"
    )  # Mock enough redis to get to the log messages
    reply = await get_reply_for_message(json.dumps(msg_contents))

    log_lines = json_log()
    print(reply)
    log_lines = log_lines.out
    assert log_lines[0]["request_id"] == "DUMMY_API_REQUEST_ID"
    assert log_lines[0]["action"] == "run_query"
    assert log_lines[0]["logger"] == "flowmachine.query_run_log"
