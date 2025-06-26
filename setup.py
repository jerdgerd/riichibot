from setuptools import find_packages, setup

setup(
    name="riichi-mahjong",
    version="0.1.0",
    description="A complete Riichi Mahjong engine implementation",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
    install_requires=[
        "dataclasses-json>=0.5.9",
        "typing-extensions>=4.7.1",
        "flask>=2.3.2",
        "flask-socketio>=5.3.4",
        "redis>=4.6.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-xdist>=3.3.1",
            "pytest-mock>=3.11.1",
            "black>=23.7.0",
            "flake8>=6.0.0",
            "mypy>=1.5.1",
            "pre-commit>=3.3.3",
            "debugpy>=1.6.7",
        ]
    },
    entry_points={
        "console_scripts": [
            "mahjong-engine=main:main",
            "mahjong-web=web_server:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
