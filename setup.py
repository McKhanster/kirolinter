from setuptools import setup, find_packages

setup(
    name="kirolinter",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click>=8.1.3",
        "pyyaml>=6.0",
        "gitpython>=3.1.43",
    ],
    entry_points={
        "console_scripts": [
            "kirolinter = kirolinter.cli:cli",
        ],
    },
    author="Khan Tran",
    author_email="khanster408@gmail.com",
    description="AI-driven code review tool for Python codebases",
    license="MIT",
    url="https://github.com/McKhanster/kirolinter",
)
