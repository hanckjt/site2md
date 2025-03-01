from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="site2md",
    version="0.1.0",
    description="将网站内容转换为Markdown文档",
    author="Hank Jing",
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "site2md=site2md.main:main",
        ],
    },
    python_requires=">=3.6",
)
