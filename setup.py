from setuptools import setup, find_packages

setup(
    name="watchman-nids",
    version="1.0.0",
    description="WatchMan Network Intrusion Detection System",
    author="Ribert Kandi Junior",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.115",
        "uvicorn[standard]>=0.30",
        "pydantic>=2.0",
        "PyJWT>=2.8",
        "bcrypt>=4.1",
        "typer>=0.12",
        "rich>=13.0",
        "requests>=2.31",
        "scapy>=2.6",
        "numpy>=1.26",
        "pandas>=2.0",
        "scikit-learn>=1.4",
        "joblib>=1.3",
        "web3>=7.0",
        "pytest>=8.0",
        "httpx>=0.27",
        "pyinstaller>=6.0",
    ],
    entry_points={
        "console_scripts": [
            "watchman=src.cli:app",
        ],
    },
)
