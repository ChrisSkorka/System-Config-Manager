from setuptools import setup, find_packages

root_package = 'sysconf'

setup(
    name=root_package,
    version='0.1',
    packages=[root_package] + [
        f"{root_package}.{item}" 
        for item in find_packages(where=root_package)
    ],
)
