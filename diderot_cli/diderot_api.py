import click
import glob
import re
import requests
import time
import urllib.parse

from contextlib import ExitStack, contextmanager
from functools import wraps
from pathlib import Path

import diderot_cli.constants as constants

from diderot_cli.context import DiderotContext
from diderot_cli.models import Book, Chapter, Course, Lab, Part
from diderot_cli.utils import (
    APIError,
    download_file_helper,
    err_for_code,
    exit_with_error,
    expand_file_path,
    debug,
    warn,
)

class DiderotClient:
    """
    DiderotClient is a wrapper around a requests.Session that maintains login
    state and simplifies some Diderot API access.
    """

    def __init__(self, base_url):
        self.url = base_url
        self.token_header = {}
        self.client = requests.session()

    def login(self, username, password):
        """Log in to Diderot to get the authentication token"""

        login_data = {
            "username": username,
            "password": password,
        }
        login_url = urllib.parse.urljoin(self.url, constants.LOGIN_URL)
        debug(f"Logging in: URL({login_url}) with credentials ({login_data})")
        r = self.client.post(login_url, data=login_data)
        if len(r.history) > 0:
            code = r.history[0].status_code
        else:
            code = r.status_code

        if not code == 200:
            exit_with_error(err_for_code(code, r))
        token = r.json()["key"]
        self.token_header = {"Authorization": f"Token {token}"}

    def get(self, api, params=None):
        """
        get is a wrapper around requests.Session.get that raises an exception
        when a request does not succeed.
        """

        url = urllib.parse.urljoin(self.url, api)
        debug(f"Request: {url}")
        response = self.client.get(url, headers=self.token_header, params=params)
        debug(f"Response [{response.status_code}]: {response.json()}")
        if response.status_code < 200 or response.status_code >= 300:
            raise err_for_code(response.status_code, response=response)
        return response

    def post(self, api, data=None, files=None, params=None):
        """
        post is a wrapper around requests.Session.post that raises an exception
        when a request does not succeed.
        """
        url = urllib.parse.urljoin(self.url, api)
        response = self.client.post(url, headers=self.token_header, data=data, files=files, params=params)
        if response.status_code < 200 or response.status_code >= 300:
            raise err_for_code(response.status_code, response=response)

    def patch(self, api, data=None, files=None, params=None):
        """
        patch is a wrapper around requests.Session.patch that raises an exception
        when a request does not succeed.
        """
        url = urllib.parse.urljoin(self.url, api)
        response = self.client.patch(url, headers=self.token_header, data=data, files=files, params=params)
        if response.status_code < 200 or response.status_code >= 300:
            raise err_for_code(response.status_code, response=response)

    def close(self):
        """Closes the connection to Diderot."""
        self.client.close()


class DiderotAPIInterface:
    """DiderotAPIInterface provides an interface to some Diderot actions."""

    def __init__(self, base_url, client_class=DiderotClient):
        self.client = client_class(base_url)

    def login(self, username, password):
        "Logs in to Diderot."
        self.client.login(username, password)

    def close(self):
        """Closes the client connection."""
        self.client.close()

    def submit_assignment(self, course_label, homework_name, filepath):
        course = Course(self.client, course_label)
        lab = Lab(course, homework_name)
        # TODO (rohany): Return more information in the response, such as:
        #  homework due date, whether its the latest homework or not, etc.
        #  All this extra stuff that the student would need to confirm
        #  if they want to submit to this assignment.
        full_path = expand_file_path(filepath)

        with open(full_path, "rb") as f:
            files = {"submission_tar": f}
            self.client.post(constants.SUBMIT_ASSIGNMENT_API.format(course.pk, lab.pk), files=files)
        # TODO (rohany): Add back in the URL to view the submission at once
        #  I understand how the react server is deployed.

    def download_assignment(self, course_label: str, homework_name: str):
        course = Course(self.client, course_label)
        lab = Lab(course, homework_name)

        attached_file_urls_endpoint = constants.FILE_URLS_API.format(course.pk, lab.pk)

        r = self.client.get(attached_file_urls_endpoint)

        downloaded = False

        for key, url in r.json().items():
            kind = re.sub(r"_url$", "", key)
            try:
                download_file_helper(url)
                downloaded = True
            except APIError as e:
                debug(e)
                click.echo(f"Could not find a {kind} for assignment {lab.name}")
            except FileExistsError as e:
                click.echo(e)

        return downloaded

    def update_assignment(self, course_label: str, homework_name: str, **options):
        course = Course(self.client, course_label)
        lab = Lab(course, homework_name)
        # Send a request to the UploadCodeLabFiles view with the target
        # files in the request.
        files = {}
        if options.get("autograde_tar") is not None:
            files["autograder-tar"] = open(expand_file_path(options.get("autograde_tar")), "rb")
        if options.get("autograde_makefile") is not None:
            files["autograder-makefile"] = open(expand_file_path(options.get("autograde_makefile")), "rb")
        if options.get("handout") is not None:
            files["handout"] = open(expand_file_path(options.get("handout")), "rb")

        # If there are no input files, return.
        if len(files) == 0:
            return

        self.client.patch(constants.UPLOAD_FILES_API.format(course.pk, lab.pk), files=files)
        for _, v in files.items():
            v.close()

    def list_books(self, course_label: str, all: bool):
        course = None
        if not all:
            if course_label == "":
                raise APIError("A course label is required if not listing all books.")
            course = Course(self.client, course_label)
        books = Book.list(self.client, course=course)
        if not all:
            return books
        else:
            # Filter the books by what courses can be seen. Turn the result
            # into a map for easy lookup.
            course_dict = dict([(course["id"], course) for course in Course.list(self.client)])
            return [book for book in books if book["course"] in course_dict]

    def create_part(self, course_label, book_label, title, **options):
        course = Course(self.client, course_label)
        book = Book(course, book_label)
        if Part.exists(course, book, options.get(constants.PART_NUMBER_GET)):
            raise APIError(
                "Existing part for Course: {}, Book: {}, and Number: {} found.".format(course.label, book.label, options.get(constants.PART_NUMBER_GET))
            )
        Part.create(course, book, title, options.get(constants.PART_NUMBER_GET), options.get(constants.PART_LABEL_GET))

    def create_book(self, course_label, title, label):
        course = Course(self.client, course_label)

        if Book.exists(course, label):
            raise APIError(
                "Existing book for Course: {}, and Label: {} found.".format(course.label, label)
            )
        Book.create(course, title, label)

    def create_chapter(self, course_label, book_label, **options):
        course = Course(self.client, course_label)
        book = Book(course, book_label)
        if options.get(constants.PART_NUMBER_GET) is None:
            raise APIError(f"--{constants.PART_NUMBER} must be set.")
        part = Part(course, book, options.get(constants.PART_NUMBER_GET))
        # See if a chapter like this exists already.
        if Chapter.exists(course, book, options.get(constants.CHAPTER_NUMBER_GET)):
            raise APIError(
                "Existing chapter for Course: {}, Book: {} and Number: {} found.".format(
                    course.label, book.label, options.get(constants.CHAPTER_NUMBER_GET)
                )
            )

        Chapter.create(course, book, part, options.get(constants.CHAPTER_NUMBER_GET), **options)

    def release_unrelease_chapter(self, course_label, book_label, release, **options):
        course = Course(self.client, course_label)
        book = Book(course, book_label)
        chapter = Chapter(course, book, options.get(constants.CHAPTER_NUMBER_GET), options.get(constants.CHAPTER_LABEL_GET))
        route_params = {
            "course_id": course.pk,
            "book_id": book.pk,
            "chapter_id": chapter.pk,
            "action": "publish" if release else "retract",
        }
        self.client.post(
            constants.MANAGE_CHAPTER_WITH_ACTION_API.format(**route_params)
        )

    def set_publish_date(self, course_label, book_label, **options):
        course = Course(self.client, course_label)
        book = Book(course, book_label)
        chapter = Chapter(course, book, options.get(constants.CHAPTER_NUMBER_GET), options.get(constants.CHAPTER_LABEL_GET))
        route_params = {
            "course_id": course.pk,
            "book_id": book.pk,
            "chapter_id": chapter.pk,
        }
        data = {}
        if options.get(constants.PUBLISH_DATE_GET):
            data["date_release"] = options.get(constants.PUBLISH_DATE_GET)
        elif options.get(constants.PUBLISH_ON_WEEK_GET):
            data["publish_on_week"] = options.get(constants.PUBLISH_ON_WEEK_GET)
        self.client.patch(
            constants.MANAGE_CHAPTER_API.format(**route_params), data=data
        )

    def upload_chapter(self, course_label: str, book_label: str, number: str, label: str, **options):
        course = Course(self.client, course_label)
        book = Book(course, book_label)
        chapter = Chapter(course, book, number, label)

        pdf_filename = options.get(constants.PDF_GET)
        xml_filename = options.get(constants.XML_GET)
        xml_pdf_filename = options.get(constants.XML_PDF_GET)
        video_url = options.get(constants.VIDEO_URL_GET)
        sleep_time = options.get(constants.SLEEP_TIME_GET, 5)
        attach = options.get(constants.ATTACH_GET, [])

        data = {}
        # Populate the input set of files.
        files = []
        if pdf_filename is not None:
            if not pdf_filename.lower().endswith(".pdf"):
                raise APIError("PDF argument must be a PDF file.")
            files.append(("input_file_pdf", Path(pdf_filename)))
        elif xml_filename is not None:
            if not (xml_filename.lower().endswith(".xml") or xml_filename.lower().endswith(".mlx")):
                raise APIError("XML argument must be an XML or MLX file.")
            files.append(("input_file_xml", Path(xml_filename)))

            if attach:
                for fg in attach:
                    base_path = Path(fg)
                    file_glob = glob.glob(expand_file_path(fg))
                    if not base_path.exists() and len(file_glob) == 0:
                        click.echo(f"Warning: cannot find file {fg}. Skipping.")
                        continue
                    for g in file_glob:
                        f = Path(g).expanduser()
                        if f.is_dir():
                            # If it is a directory, include all children.
                            files.extend([("attachments", m) for m in f.glob("**/*")])
                        else:
                            # If it is a file, add it directly.
                            files.append(("attachments", f))
            if xml_pdf_filename is not None:
                files.append(("input_file_pdf", Path(xml_pdf_filename)))

        if video_url is not None:
            data["video_url"] = video_url

        for _, p in files:
            click.echo(f"Uploading file: {p.name}")

        if pdf_filename is not None or xml_filename is not None:
            with ExitStack() as stack:
                opened_files = [
                    (typ, (path.name, stack.enter_context(path.expanduser().open("rb")))) for typ, path in files
                ]

                route_params = {
                    "course_id": course.pk,
                    "book_id": book.pk,
                    "chapter_id": chapter.pk,
                    "action": "content_upload"
                }
                self.client.post(
                    constants.MANAGE_CHAPTER_WITH_ACTION_API.format(**route_params),
                    data=data,
                    files=opened_files
                )

            # Wait until the book becomes unlocked.
            while True:
                click.echo("Waiting for book upload to complete...")
                time.sleep(sleep_time)
                if not Book.check_is_locked(self.client, book.pk):
                    break

            # Get back error and warning information from uploading.
            warnings, errors = Chapter.get_warnings_and_errors(self.client, chapter.pk)

#            if len(warnings) != 0:
#                [warn(w) for w in warnings]
            if warnings:
                warn(warnings)
            if len(errors) != 0:
                raise APIError(str(errors))


@contextmanager
def setup_client(dc: DiderotContext):
    dc.client = DiderotAPIInterface(dc.url)

    try:
        if dc.username is None:
            creds = constants.DEFAULT_CRED_LOCATIONS
            if dc.credentials is not None:
                creds = [dc.credentials] + creds
            for c in creds:
                p = Path(c).expanduser()

                if not p.is_file() and c == dc.credentials:
                    exit_with_error(f"Credentials path `{c}` is invalid.")

                if not p.exists():
                    continue

                if (p.stat().st_mode & 0o177 != 0):
                    exit_with_error(
                        f"Credentials file `{c}` must have 0600 permissions."
                        " Run `chmod 600 <credentials>` first."
                    )
                with p.open("r") as f:
                    data = f.read().strip().split("\n")
                    if len(data) < 2:
                        exit_with_error(f"Credentials file `{c}` does not contain proper credentials.")
                    dc.username = data[0]
                    dc.password = data[1]
                break

        if dc.username is None:
            dc.username = click.prompt("Username")
        if dc.password is None:
            dc.password = click.prompt(text="Password", hide_input=True)

        dc.client.login(dc.username, dc.password)
        yield dc.client
    finally:
        dc.client.close()

def uses_api(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        ctx = click.get_current_context()

        with setup_client(ctx.obj):
            try:
                f(*args, **kwargs)
            except APIError as e:
                exit_with_error(str(e))

    return wrapper
