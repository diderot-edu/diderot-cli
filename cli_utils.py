import json
import os
import shutil

import requests


# APIError is an exception raised by the API.
class APIError(Exception):
    pass


class BookNotFoundAPIError(APIError):
    pass


# expand_file_path expands a relative path into a full path.
def expand_file_path(path):
    return os.path.abspath(os.path.expandvars(os.path.expanduser(path)))


# singleton_or_none returns a single element from a response json or
# none if the response is not a singleton.
def singleton_or_none(response):
    if len(response.json()) != 1:
        return None
    return response.json()[0]


# err_for_code returns an appropriate error message for HTTP errors.
def err_for_code(code, response=None):
    if code == 200:
        return APIError("Authentication failed. Your credentials might be incorrect")
    elif code == 301:
        return APIError("Could not connect to the specified url.")
    elif code == 404:
        return APIError("Unable to connect to Diderot (error 404)")
    elif code >= 500:
        return APIError("Server failed to fulfill request for main page")
    else:
        try:
            if response is not None and getattr(response, "json") and response.json():
                return APIError(f"Unhandled status code {code}, {response.json()}")
        except json.decoder.JSONDecodeError:
            return APIError(f"Unhandled status code {code}, error {response.content}")

        return APIError(f"Unhandled status code {code}")


# download_file_helper abstracts logic for downloading a file and potentially
# aborting if the same file already exists locally.
def download_file_helper(url):
    r = requests.get(url, stream=True)
    if r.status_code != 200:
        raise APIError("Non 200 status code when downloading {}".format(url))
    local_filename = url.split("/")[-1]
    if os.path.isfile(local_filename):
        raise FileExistsError(
            "There is already a file called {}, so I won't download a new one."
            " Rename the old one and please try again".format(local_filename)
        )
    print("Trying to download file to {}".format(local_filename))
    with open(local_filename, "wb") as f:
        shutil.copyfileobj(r.raw, f)


# Utility function for pretty printing of list data within the terminal size.
def print_list(items):
    try:
        cols, _ = os.get_terminal_size(0)
    except Exception:
        cols = 40
    if len(items) == 0:
        maxLen = 20
    else:
        maxLen = max([len(x) for x in items]) + 2
    n = max(((cols // maxLen) - 1), 1)
    final = [items[i * n : (i + 1) * n] for i in range((len(items) + n - 1) // n)]
    for row in final:
        print(" ".join(["{: <" + str(maxLen) + "}"] * len(row)).format(*row))
