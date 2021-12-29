import click
import json
import os
import requests
import shutil
import sys

from functools import wraps
from urllib.parse import urlparse, unquote_plus as unquote

from diderot_cli.context import DiderotContext, pass_diderot_context

class APIError(Exception):
    pass

class BookNotFoundAPIError(APIError):
    pass

def expand_file_path(path):
    """expand_file_path expands a relative path into a full path."""
    return os.path.abspath(os.path.expandvars(os.path.expanduser(path)))


def singleton_or_none(response):
    """
    singleton_or_none returns a single element from a response json or
    none if the response is not a singleton.
    """

    if len(response.json()) != 1:
        return None
    return response.json()[0]


def err_for_code(code, response=None):
    """err_for_code returns an appropriate error message for HTTP errors."""

    debug(f"{code}: {response.content}")

    if code == 200:
        return APIError("Authentication failed. Your credentials might be incorrect")
    elif code == 301:
        return APIError("Could not connect to the specified url")
    elif code == 404:
        return APIError("Unable to connect to Diderot (error 404)")
    elif code >= 500:
        return APIError("Server failed to fulfill request for main page")
    else:
        if response is not None:
            try:
                if getattr(response, "json") and response.json():
                    return APIError(f"Unhandled status code: {code}, {response.json()}")
                else:
                    return APIError(f"Unhandled status code: {code}, error: {response.content}")
            except json.decoder.JSONDecodeError:
                return APIError(f"Unhandled status code: {code}, error: {response.content}")

        return APIError(f"Unhandled status code: {code}")


def download_file_helper(url):
    """
    download_file_helper abstracts logic for downloading a file and potentially
    aborting if the same file already exists locally.
    """

    r = requests.get(url, stream=True)
    if r.status_code != 200:
        raise APIError("Non 200 status code when downloading {}".format(url))
    local_filename = unquote(urlparse(url).path.split("/")[-1])
    if os.path.isfile(local_filename):
        raise FileExistsError("File {} already exists, aborting".format(local_filename))
    click.echo("Downloading {}...".format(local_filename))
    with open(local_filename, "wb") as f:
        shutil.copyfileobj(r.raw, f)


def print_list(items):
    """Utility function for pretty printing of list data within the terminal size."""

    try:
        cols, _ = shutil.get_terminal_size()
    except Exception:
        cols = 40
    if len(items) == 0:
        maxLen = 20
    else:
        maxLen = max([len(x) for x in items]) + 2
    n = max(((cols // maxLen) - 1), 1)
    final = [items[i * n : (i + 1) * n] for i in range((len(items) + n - 1) // n)]
    for row in final:
        click.echo(" ".join(["{: <" + str(maxLen) + "}"] * len(row)).format(*row))


def exit_with_error(error_msg):
    """exit_with_error prints an error message and exits with ret code 1."""
    click.secho(f"[ERROR]: {error_msg}", fg="red", err=True)
    sys.exit(1)


def debug(message):
    ctx: DiderotContext = click.get_current_context().obj

    if ctx.debug:
        click.secho(f"[DEBUG]: {message}", fg="yellow", err=True)

def warn(message):
    click.secho(f"Warning: {message}", fg="yellow")


