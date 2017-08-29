from setuptools import setup, find_packages

setup(
    name='auto-tracking-cctv-gateway',
    version='1.0',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'run-cctv-gateway = gateway.__main__:main'
        ]
    }
)
