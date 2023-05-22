from setuptools import setup, find_namespace_packages

setup(
    name="diderot-cli",
    version="0.1.0",
    packages=find_namespace_packages(include=["diderot_cli", "diderot_cli.*"]),
    install_requires=[
        "click==8.0.1",
        "requests==2.31.0",
    ],
    entry_points={
        "console_scripts": [
            "diderot = diderot_cli.commands:diderot",
            "diderot_admin = diderot_cli.commands.diderot_admin:admin",
            "diderot_student = diderot_cli.commands.diderot_user:student",
        ],
    },
)
