from setuptools import setup, find_packages

setup(
    name="kirolinter",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click>=8.1.3",
        "pyyaml>=6.0",
        "gitpython>=3.1.43",
        "langchain>=0.1.0",
        "apscheduler>=3.10.0",
        "psutil>=5.9.0",
        "redis>=4.5.0",
        "scikit-learn>=1.3.0",
        "numpy>=1.24.0",
        "pytest>=7.0.0",
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
