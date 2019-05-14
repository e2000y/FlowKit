# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# -*- coding: utf-8 -*-
"""
Contains the definition of callables to be used in the production ETL dag.
"""
import logging

from pathlib import Path

from airflow.models import DagRun, BaseOperator
from airflow.hooks.dbapi_hook import DbApiHook

# pylint: disable=unused-argument
def render_and_run_sql_callable(
    *,
    dag_run: DagRun,
    task: BaseOperator,
    db_hook: DbApiHook,
    config_path: Path,
    template_name: str,
    **kwargs,
):
    """
    This function takes information from the DagRun conf to locate
    the correct sql template file, uses the DagRun conf to populate the
    template and runs it against the DB.

    Parameters
    ----------
    dag_run : DagRun
        Passed as part of the Dag context - contains the config.
    task : BaseOperator
        Passed as part of the Dag context - provides access to the instantiated
        operator this callable is running in.
    db_hook : DbApiHook
        A hook to a DB - will most likely be the PostgresHook but could
        be other types of Airflow DB hooks.
    config_path : Path
        Location of flowelt config directory - where templates are stored.
    template_name : str
        The file name sans .sql that we wish to template. Most likely the
        same as the task_id.
    """
    # dag_run.conf["template_path"] -> where the sql templates
    # for this dag run live. Determined nby the type of the CDR
    # this dag is ingesting. If this is voice then template_path
    # will be 'etl/voice'...
    template_path = config_path / dag_run.conf["template_path"]

    # template name matches the task_id this is being used
    # in .If this is the transform task then will be transform'
    # and thus the template we use will be 'etl/voice/transform.sql'
    template_path = template_path / f"{template_name}.sql"
    template = open(template_path).read()

    # make use of the Operators templating functionality
    sql = task.render_template("", template, dag_run.conf)

    # run the templated sql against DB
    db_hook.run(sql=sql)


# pylint: disable=unused-argument
def success_branch_callable(*, dag_run: DagRun, **kwargs):
    """
    Function to determine if we should follow the quarantine or
    the archive branch. If no downstream tasks have failed we follow
    archive branch and quarantine otherwise.
    """
    previous_task_failures = [
        dag_run.get_task_instance(task_id).state == "failed"
        for task_id in ["init", "extract", "transform", "load"]
    ]

    logging.info(dag_run)

    if any(previous_task_failures):
        branch = "quarantine"
    else:
        branch = "archive"

    return branch
