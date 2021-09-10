from setuptools import setup, find_packages

setup(
    name="diderot-cli",
    version="0.1.0",
    py_modules=[
        "arguments",
        "constants",
        "context",
        "diderot_api",
        "models",
        "options",
        "utils",
    ],
    packages=find_packages(),
    install_requires=[
        "click==8.0.1",
        "requests==2.22.0",
    ],
    entry_points={
        "console_scripts": [
            "diderot = commands:diderot",
        ],
    },
)
