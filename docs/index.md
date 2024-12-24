
![cicd](https://github.com/thebjorn/seeqret/actions/workflows/ci.yml/badge.svg)
[![codecov](https://codecov.io/gh/thebjorn/seeqret/graph/badge.svg?token=5PQOZLTSYD)](https://codecov.io/gh/thebjorn/seeqret)
[![pypi](https://img.shields.io/pypi/v/seeqret?label=pypi%20seeqret)](https://pypi.org/project/seeqret/)
[![downloads](https://pepy.tech/badge/seeqret)](https://pepy.tech/project/seeqret)
<a href="https://github.com/thebjorn/seeqret"><img src="github-mark/github-mark.png" width="25" height="25"></a>

![codecov](https://codecov.io/gh/thebjorn/seeqret/graphs/sunburst.svg?token=5PQOZLTSYD)

# <img src="seeqret-logo-256.png" width=100> Seeqret: Safely transferring code secrets
(very much a work in progress)


<!-- @import "[TOC]" {cmd="toc" depthFrom=1 depthTo=6 orderedList=false} -->

<!-- code_chunk_output -->

- [Seeqret: Safely transferring code secrets](#seeqret-safely-transferring-code-secrets)
  - [Introduction](#introduction)
    - [Prior art...](#prior-art)
  - [Assumptions](#assumptions)
  - [Minimum Requirements](#minimum-requirements)
- [Use cases](#use-cases)
- [Code](#code)

<!-- /code_chunk_output -->


## Introduction

How do you communicate the set of secrets (passwords, API keys, etc.) that your code needs to run? You can't just write them in the code, because that would expose them to anyone who can read the code. You can't just send them in an email, because that would expose them to anyone who can read your email. You can't just write them on a sticky note, because that would expose them to anyone who can read your sticky note.
