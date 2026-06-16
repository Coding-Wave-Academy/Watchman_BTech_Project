from setuptools import setup, find_packages

setup(
    name="watchman-nids",
    version="1.0.0",
    description="WatchMan Network Intrusion Detection System",
    author="Ribert Kandi Junior",
    packages=find_packages(),
    install_requires=[
        # Core requirements should be here, though we rely on requirements.txt for now
    ],
    entry_points={
        "console_scripts": [
            "watchman=src.cli:app",
        ],
    },
)
