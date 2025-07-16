import inspect
import pathlib
import subprocess

from invoke import task

if not hasattr(inspect, "getargspec"):
    inspect.getargspec = inspect.getfullargspec

ROOT = pathlib.Path(__file__).parent.resolve().as_posix()
utests_completed_process = None
atests_completed_process = None


@task
def utests(context):
    cmd = [
        "coverage",
        "run",
        "--source=src/RobotAid",
        "-p",
        "-m",
        "pytest",
        "--junitxml=results/pytest.xml",
        f"{ROOT}/tests/utest",
    ]
    global utests_completed_process
    utests_completed_process = subprocess.run(" ".join(cmd), shell=True, check=False)


@task
def atests(context):
    cmd = [
        "coverage",
        "run",
        "--source=src/RobotAid",
        "-p",
        "-m",
        "robot",
        "--loglevel=TRACE:DEBUG",
        "--listener RobotStackTracer",
        "-d results",
        "--prerebotmodifier utilities.xom.XUnitOut:results/xunit.xml",
        "--exclude not_ci",
        f"{ROOT}/tests/atest",
    ]
    global atests_completed_process
    atests_completed_process = subprocess.run(" ".join(cmd), shell=True, check=False)


@task(utests, atests)
def tests(context):
    subprocess.run("coverage combine", shell=True, check=False)
    subprocess.run("coverage report", shell=True, check=False)
    subprocess.run("coverage html -d results/htmlcov", shell=True, check=False)
    if (
        utests_completed_process.returncode != 0
        or atests_completed_process.returncode != 0
    ):
        raise Exception("Tests failed")


@task
def coverage_report(context):
    subprocess.run("coverage combine", shell=True, check=False)
    subprocess.run("coverage report", shell=True, check=False)
    subprocess.run("coverage html -d results/htmlcov", shell=True, check=False)
