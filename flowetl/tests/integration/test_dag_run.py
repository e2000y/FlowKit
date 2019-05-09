import os
from time import sleep

from subprocess import DEVNULL, STDOUT, Popen

from airflow.models import DagRun


def test_foo(airflow_local_setup_fnc_scope):

    airflow_run_cmd = airflow_local_setup_fnc_scope["airflow_run_cmd"]

    p = airflow_run_cmd("airflow unpause etl_sensor", shell=False)
    p.wait()
    p = airflow_run_cmd("airflow unpause etl", shell=False)
    p.wait()
    p = airflow_run_cmd("airflow trigger_dag etl_sensor", shell=False)
    p.wait()

    while not DagRun.find("etl", state="success"):
        sleep(1)

    assert True


def test_bar(airflow_local_setup_fnc_scope):

    airflow_run_cmd = airflow_local_setup_fnc_scope["airflow_run_cmd"]

    p = airflow_run_cmd("airflow unpause etl_sensor", shell=False)
    p.wait()
    p = airflow_run_cmd("airflow unpause etl", shell=False)
    p.wait()
    p = airflow_run_cmd("airflow trigger_dag etl_sensor", shell=False)
    p.wait()

    while not DagRun.find("etl", state="success"):
        sleep(1)

    assert True
