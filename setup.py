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
        'cryptography'
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
    ],
    long_description=open('README.md').read(),
    packages=setuptools.find_packages(),
    zip_safe=False,
)