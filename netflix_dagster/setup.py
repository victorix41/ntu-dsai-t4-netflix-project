from setuptools import find_packages, setup

setup(
    name="netflix_dagster",
    packages=find_packages(exclude=["netflix_dagster_tests"]),
    install_requires=[
        "dagster",
        "dagster-cloud"
    ],
    extras_require={"dev": ["dagster-webserver", "pytest"]},
)
