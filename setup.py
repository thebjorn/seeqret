"""
Safely transferring code secrets.
"""

import setuptools

version = '0.1.7'

setuptools.setup(
    name='seeqret',
    description='Safely transferring code secrets',
    keywords='secrets, gpg, pgp',
    version=version,
    author='Bjorn',
    url='https://github.com/thebjorn/seeqret.git',
    install_requires=[
        'rsa',
        'python-gnupg',
        'cryptography',
        'pynacl',
        'Click',
        'rich',
        'requests',
        "pywin32  ; sys_platform == 'win32'"
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
    long_description_content_type='text/markdown',
    packages=setuptools.find_packages(),
    include_package_data=True,
    zip_safe=False,
)
