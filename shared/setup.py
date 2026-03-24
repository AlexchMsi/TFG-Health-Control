from setuptools import setup, find_packages

setup(
    name="ot-health-shared",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "influxdb-client>=1.44.0",
        "pydantic-settings>=2.2.1",
        "structlog>=24.1.0",
    ],
)
