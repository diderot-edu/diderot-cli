# Structure

The CLI's parsers and dispatch methods are in `standalone.py`. `standalone.py` creates two main classes, `DiderotUser` and `DiderotAdmin` which implement the corresponding CLI's. These classes dispatch requests to Diderot through the `DiderotAPIInterface`, which is defined in `api_calls.py`.

# Testing

Unit tests created with python3's `unittest` package are in `test.py`. These tests create a sample `DiderotUser` or `DiderotAdmin` and run various commands against them, and expect certain output. The CLI instances connect to a fake Diderot webserver which sends back sample API data.

# Goals / TODO's

* Keep this super simple.  it should work with just bare python
  so that the users can use it without having to create a venv and
  install bunch of packages.

* We could provide a interface to the latex to xml compiler via the
  cli.  this would allow the users to try things out without having to
  install the compiler.
