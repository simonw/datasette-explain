# datasette-explain

[![PyPI](https://img.shields.io/pypi/v/datasette-explain.svg)](https://pypi.org/project/datasette-explain/)
[![Changelog](https://img.shields.io/github/v/release/simonw/datasette-explain?include_prereleases&label=changelog)](https://github.com/simonw/datasette-explain/releases)
[![Tests](https://github.com/simonw/datasette-explain/workflows/Test/badge.svg)](https://github.com/simonw/datasette-explain/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/simonw/datasette-explain/blob/main/LICENSE)

Explain SQL queries executed using Datasette

## Installation

Install this plugin in the same environment as Datasette.

    datasette install datasette-explain

## Usage

The plugin adds JavaScript to the query editor page which will constantly update the page with information gained from running EXPLAIN QUERY PLAN queries against the entered SQL.

This may result in an error message, or it may show the query plan along with any tables used by the query.

## Development

To set up this plugin locally, first checkout the code. Then create a new virtual environment:

    cd datasette-explain
    python3 -m venv venv
    source venv/bin/activate

Now install the dependencies and test dependencies:

    pip install -e '.[test]'

To run the tests:

    pytest
