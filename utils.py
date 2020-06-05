import os
import shutil

import requests


# APIError is an exception raised by the API.
class APIError(Exception):
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
def err_for_code(code):
    if code == 404:
        return APIError("Unable to connect to Diderot (error 404)")
    if code >= 500:
        return APIError("Server failed to fulfill request for main page")
    if code == 200:
        return APIError("Authentication failed. Your credentials might be incorrect")


# download_file_helper abstracts logic for downloading a file and potentially
# aborting if the same file already exists locally.
def download_file_helper(url):
    r = requests.get(url, stream=True)
    if r.status_code != 200:
        return
    local_filename = url.split("/")[-1]
    if os.path.isfile(local_filename):
        raise APIError(
            "There is already a file called {}, so I won't download a new one."
            " Rename the old one and please try again".format(local_filename)
        )
    print("Trying to download file to {}".format(local_filename))
    with open(local_filename, "wb") as f:
        shutil.copyfileobj(r.raw, f)


# Utility function for pretty printing of list data within the terminal size.
def print_list(l):
    try:
        cols, _ = os.get_terminal_size(0)
    except:
        cols = 40
    if len(l) == 0:
        maxLen = 20
    else:
        maxLen = max([len(x) for x in l]) + 2
    n = max(((cols // maxLen) - 1), 1)
    final = [l[i * n : (i + 1) * n] for i in range((len(l) + n - 1) // n)]
    for row in final:
        print(" ".join(["{: <" + str(maxLen) + "}"] * len(row)).format(*row))
