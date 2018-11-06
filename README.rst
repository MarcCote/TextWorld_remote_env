========
Overview
========

.. start-badges

.. list-table::
    :stub-columns: 1

    * - docs
      - |docs|
    * - tests
      - | |travis|
        | |coveralls| |codecov|
    * - package
      - | |version| |wheel| |supported-versions| |supported-implementations|
        | |commits-since|

.. |docs| image:: https://readthedocs.org/projects/TextWorld_remote_env/badge/?style=flat
    :target: https://readthedocs.org/projects/TextWorld_remote_env
    :alt: Documentation Status


.. |travis| image:: https://travis-ci.org/spMohanty/TextWorld_remote_env.svg?branch=master
    :alt: Travis-CI Build Status
    :target: https://travis-ci.org/spMohanty/TextWorld_remote_env

.. |coveralls| image:: https://coveralls.io/repos/spMohanty/TextWorld_remote_env/badge.svg?branch=master&service=github
    :alt: Coverage Status
    :target: https://coveralls.io/r/spMohanty/TextWorld_remote_env

.. |codecov| image:: https://codecov.io/github/spMohanty/TextWorld_remote_env/coverage.svg?branch=master
    :alt: Coverage Status
    :target: https://codecov.io/github/spMohanty/TextWorld_remote_env

.. |version| image:: https://img.shields.io/pypi/v/textworld-remote-env.svg
    :alt: PyPI Package latest release
    :target: https://pypi.python.org/pypi/textworld-remote-env

.. |commits-since| image:: https://img.shields.io/github/commits-since/spMohanty/TextWorld_remote_env/v0.1.0.svg
    :alt: Commits since latest release
    :target: https://github.com/spMohanty/TextWorld_remote_env/compare/v0.1.0...master

.. |wheel| image:: https://img.shields.io/pypi/wheel/textworld-remote-env.svg
    :alt: PyPI Wheel
    :target: https://pypi.python.org/pypi/textworld-remote-env

.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/textworld-remote-env.svg
    :alt: Supported versions
    :target: https://pypi.python.org/pypi/textworld-remote-env

.. |supported-implementations| image:: https://img.shields.io/pypi/implementation/textworld-remote-env.svg
    :alt: Supported implementations
    :target: https://pypi.python.org/pypi/textworld-remote-env


.. end-badges

Remote Env for TextWorld

* Free software: Apache Software License 2.0

Installation
============

::

    pip install textworld-remote-env

Documentation
=============


https://TextWorld_remote_env.readthedocs.io/


Development
===========

To run the all tests run::

    tox

Note, to combine the coverage data from all the tox environments run:

.. list-table::
    :widths: 10 90
    :stub-columns: 1

    - - Windows
      - ::

            set PYTEST_ADDOPTS=--cov-append
            tox

    - - Other
      - ::

            PYTEST_ADDOPTS=--cov-append tox
