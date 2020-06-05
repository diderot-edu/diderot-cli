import glob
import os
import time
import urllib.parse
from contextlib import ExitStack
from pathlib import Path

import requests

from models import (
    MANAGE_BOOK_API,
    SUBMIT_ASSIGNMENT_API,
    UPLOAD_FILES_API,
    Book,
    Chapter,
    Course,
    Lab,
    Part,
)
from utils import APIError, download_file_helper, err_for_code, expand_file_path


# DiderotClient is a wrapper around a requests.Session that maintains login
# state and simplifies some Diderot API access.
class DiderotClient:
    def __init__(self, base_url):
        self.url = base_url
        self.csrftoken = None
        self.client = None

    # connect makes the initial connection to Diderot.
    def connect(self):
        self.client = requests.session()
        main_page = self.client.get(self.url)
        code = main_page.status_code
        if not code == 200:
            raise err_for_code(code)
        self.csrftoken = self.client.cookies["csrftoken"]

    # login attempts to log into Diderot using the provided credentials.
    def login(self, username, password):
        login_data = {
            "username": username,
            "password": password,
            "csrfmiddlewaretoken": self.csrftoken,
            "next": "/courses/",
        }
        login_url = urllib.parse.urljoin(self.url, "login/login/?next=/courses/")
        r = self.client.post(login_url, data=login_data)
        if len(r.history) > 0:
            code = r.history[0].status_code
        else:
            code = r.status_code

        if not code == 302:
            raise err_for_code(code)
        self.csrftoken = self.client.cookies["csrftoken"]

    # get is a wrapper around requests.Session.get that raises an exception
    # when a request does not succeed.
    def get(self, api, params=None):
        url = urllib.parse.urljoin(self.url, api)
        response = self.client.get(url, headers={"X-CSRFToken": self.csrftoken}, params=params)
        if response.status_code != 200:
            raise err_for_code(response.status_code)
        return response

    # get is a wrapper around requests.Session.post that raises an exception
    # when a request does not succeed.
    def post(self, api, data=None, files=None, params=None):
        url = urllib.parse.urljoin(self.url, api)
        response = self.client.post(url, headers={"X-CSRFToken": self.csrftoken}, data=data, files=files, params=params)
        if response.status_code != 200:
            raise err_for_code(response.status_code)

    # close closes the connection to Diderot.
    def close(self):
        self.client.close()


# DiderotAPIInterface provides an interface to some Diderot actions.
class DiderotAPIInterface:
    def __init__(self, base_url):
        self.client = DiderotClient(base_url)

    def connect(self, username, password):
        self.client.connect()
        self.client.login(username, password)

    def submit_assignment(self, course_label, homework_name, filepath):
        course = Course(self.client, course_label)
        lab = Lab(course, homework_name)
        # TODO (rohany): Return more information in the response, such as:
        #  homework due date, whether its the latest homework or not, etc.
        #  All this extra stuff that the student would need to confirm
        #  if they want to submit to this assignment.
        full_path = expand_file_path(filepath)
        if not os.path.exists(full_path):
            raise APIError("Input file does not exist.")

        f = open(full_path, "rb")
        files = {}
        if lab.handin_type == "TR":
            files["submission_tar"] = f
        elif lab.handin_type == "FU":
            files["submission_files"] = f
        else:
            raise APIError("For copy-paste or per problem copy-paste handins, use the web interface.")
        self.client.post(SUBMIT_ASSIGNMENT_API.format(course.pk), files=files, params={"hw_pk": lab.pk})
        f.close()
        url = urllib.parse.urljoin(self.client.url, SUBMIT_ASSIGNMENT_API.format(course.pk))
        return url + "?hw_pk={}".format(lab.pk)

    def download_assignment(self, course_label, homework_name):
        course = Course(self.client, course_label)
        lab = Lab(course, homework_name)
        base_path = "http://s3.amazonaws.com/" + course.autograder_bucket + "/" + lab.name + "/"
        writeup_path = base_path + "writeup.pdf"
        handout_path = base_path + "{}-handout-{}.tgz".format(course.number, lab.name)
        for p in [writeup_path, handout_path]:
            download_file_helper(p)

    def update_assignment(self, course_label, homework_name, args):
        course = Course(self.client, course_label)
        lab = Lab(course, homework_name)
        # Send a request to the UploadCodeLabFiles view with the target
        # files in the request.
        files = {}
        if args.autograde_tar is not None:
            files["autograde-tar"] = open(expand_file_path(args.autograde_tar), "rb")
        if args.autograde_makefile is not None:
            files["autograde-makefile"] = open(expand_file_path(args.autograde_makefile), "rb")
        if args.handout is not None:
            files["handout"] = open(expand_file_path(args.handout), "rb")
        if args.writeup is not None:
            files["writeup"] = open(expand_file_path(args.writeup), "rb")

        # If there are no input files, return.
        if len(files) == 0:
            return

        self.client.post(UPLOAD_FILES_API.format(course.pk), files=files, params={"hw_pk": lab.pk})
        for _, v in files.items():
            v.close()

    def list_books(self, course_label, all=False):
        course = None
        if not all:
            if course_label is None:
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

    def create_part(self, course_label, book_label, number, title, label):
        course = Course(self.client, course_label)
        book = Book(course, book_label)
        if book.is_booklet:
            raise APIError("Part creation is disallowed on booklets.")
        if Part.exists(course, book, number):
            raise APIError(
                "Existing part for Course: {}, Book: {}, and Number: {} found.".format(course.label, book.label, number)
            )
        Part.create(course, book, title, number, label)

    def create_chapter(self, course_label, book_label, part_num, chapter_num, title, label):
        course = Course(self.client, course_label)
        book = Book(course, book_label)
        if not book.is_booklet and part_num is None:
            raise APIError("--part must be set. {} is not a booklet.".format(book.label))
        part = Part(course, book, part_num)
        # See if a chapter like this exists already.
        if Chapter.exists(course, book, chapter_num):
            raise APIError(
                "Existing chapter for Course: {}, Book: {} and Number: {} found.".format(
                    course.label, book.label, chapter_num
                )
            )
        # Actually create the chapter now.
        Chapter.create(course, book, part, chapter_num, title, label)

    def release_unrelease_chapter(self, course_label, book_label, args, release=True):
        course = Course(self.client, course_label)
        book = Book(course, book_label)
        chapter = Chapter(course, book, args.chapter_number, args.chapter_label)
        release_params = {"chapter_pk": chapter.pk}
        if release:
            release_params["kind"] = "release"
        else:
            release_params["kind"] = "unrelease"
        self.client.post(MANAGE_BOOK_API.format(course.pk, book.pk), data=release_params)

    def upload_chapter(self, course_label, book_label, args, sleep_time=5):
        course = Course(self.client, course_label)
        book = Book(course, book_label)
        chapter = Chapter(course, book, args.chapter_number, args.chapter_label)
        update_params = {"kind": "upload content", "chapter_pk": chapter.pk}

        # Populate the input set of files.
        files = []
        if args.pdf is not None:
            if not args.pdf.lower().endswith(".pdf"):
                raise APIError("PDF argument must be a PDF file.")
            files.append(("input_file_pdf", Path(args.pdf)))
            if args.video_url is not None:
                update_params["video_url_pdf"] = args.video_url
        elif args.slides is not None:
            if not args.slides.lower().endswith(".pdf"):
                raise APIError("Slides argument must be a PDF file.")
            files.append(("input_file_slide", Path(args.slides)))
            if args.video_url is not None:
                update_params["video_url_slide"] = args.video_url
        elif args.xml is not None:
            if not (args.xml.lower().endswith(".xml") or args.xml.lower().endswith(".mlx")):
                raise APIError("XML argument must be an XML or MLX file.")
            files.append(("input_file_xml", Path(args.xml)))
            if args.attach is not None:
                for fg in args.attach:
                    for g in glob.glob(expand_file_path(fg)):
                        f = Path(g).expanduser()
                        if f.is_dir():
                            # If it is a directory, include all children.
                            files.extend([("image", m) for m in f.glob("**/*")])
                        else:
                            # If it is a file, add it directly.
                            files.append(("image", f))
            if args.xml_pdf is not None:
                files.append(("input_file_xml_pdf", Path(args.xml_pdf)))

        for _, p in files:
            print("Uploading file:", p.name)

        with ExitStack() as stack:
            opened_files = [
                (typ, (path.name, stack.enter_context(path.expanduser().open("rb")))) for typ, path in files
            ]
            self.client.post(MANAGE_BOOK_API.format(course.pk, book.pk), files=opened_files, data=update_params)

        # Wait until the book becomes unlocked.
        while True:
            print("Waiting for book upload to complete...")
            time.sleep(sleep_time)
            if not Book.check_is_locked(self.client, book.pk):
                break

        # Get back error and warning information from uploading.
        warnings, errors = Chapter.get_warnings_and_errors(self.client, chapter.pk)
        if len(warnings) != 0:
            print(warnings)
        if len(errors) != 0:
            raise APIError(str(errors))
