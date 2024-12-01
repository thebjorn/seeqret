"""
Safely transferring code secrets.
"""

import setuptools

version = '0.0.1'

setuptools.setup(
    name='thebjorn-secrets',
    version=version,
    author='Bjorn',
    url='https://github/thebjorn/secrets.git',
    install_requires=[
        'rsa',
        'cryptography',
        'Click',
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
    ],
    entry_points={
        'console_scripts': [
            'seeqret=seeqret.main:cli',
        ],
    },
    long_description=open('README.md').read(),
    packages=setuptools.find_packages(),
    include_package_data=True,
    zip_safe=False,
)