import cgi
import json

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from diderot_cli.constants import ADDR, PORT, COURSE_API, BOOK_API, PARTS_API, CHAPTERS_API, LOGIN_URL

courses = [
    {"id": "0", "label": "TestCourse0", "number": "0", "s3_autograder_bucket": "test_bucket"},
    {"id": "1", "label": "TestCourse1", "number": "1", "s3_autograder_bucket": "test_bucket"},
]
codelabs = [
    {
        "id": "0",
        "name": "TestHW1",
        "course": "0",
        "course__label": "TestCourse0",
        "uuid": "",
    },
    {"id": "1", "name": "TestHW2", "course": "0", "course__label": "TestCourse0", "uuid": ""},
    {"id": "2", "name": "TestHW3", "course": "1", "course__label": "TestCourse1", "uuid": ""},
    {"id": "3", "name": "TestHW4", "course": "1", "course__label": "TestCourse1", "uuid": ""},
]

books = [
    {
        "label": "TestBook1",
        "course": "0",
        "course__label": "TestCourse0",
        "title": "TestBook1",
        "version": "1",
        "id": "0",
        # TODO (rohany): this might need to be a string
        "is_locked": False,
    },
    {
        "label": "TestBook2",
        "course": "0",
        "course__label": "TestCourse0",
        "title": "TestBook2",
        "version": "1",
        "id": "1",
        "is_locked": False,
    },
    {
        "label": "TestBook3",
        "course": "1",
        "course__label": "TestCourse1",
        "title": "TestBook3",
        "version": "1",
        "id": "2",
        "is_locked": False,
    },
    {
        "label": "TestBook4",
        "course": "1",
        "course__label": "TestCourse1",
        "title": "TestBook4",
        "version": "1",
        "id": "3",
        "is_locked": False,
    },
]

# make parts for only one course.
parts = [
    {"id": "0", "label": "TestPart1", "book": "0", "book__id": "0", "title": "TestPart1", "rank": "1"},
    {"id": "1", "label": "TestPart2", "book": "0", "book__id": "0", "title": "TestPart2", "rank": "2"},
    {"id": "2", "label": "TestPart3", "book": "1", "book__id": "1", "title": "TestPart3", "rank": "1"},
]

chapters = [
    {
        "id": "0",
        "label": "TestChapter1",
        "book": "0",
        "book__id": "0",
        "part": "0",
        "upload_errors": "",
        "upload_warnings": "",
        "title": "TestChapter1",
        "rank": "1",
        "course__label": "TestCourse0",
        "course__id": "0",
    },
    {
        "id": "1",
        "label": "TestChapter2",
        "book": "0",
        "book__id": "0",
        "part": "1",
        "upload_errors": "",
        "upload_warnings": "",
        "title": "TestChapter2",
        "rank": "2",
        "course__label": "TestCourse0",
        "course__id": "0",
    },
]


# TODO (rohany): This seems unlikely, but maybe theres a way to run an actual
# mini-server of diderot here?
# Create an HTTP server handler to pretend to be Diderot to do some verification.
class DiderotHTTPHandler(BaseHTTPRequestHandler):

    # useful json wrapper
    def dump(self, obj):
        js = json.dumps(obj)
        return js.encode()

    # access GET parameters
    def get_params(self):
        query = urlparse(self.path).query
        fields = parse_qs(query)
        return dict([(str(k), str(v[0])) for k, v in fields.items()])

    def post_params(self):
        data = self.rfile.read(int(self.headers["Content-Length"])).decode()
        fields = parse_qs(data)
        return dict([(str(k), str(v[0])) for k, v in fields.items()])

    # Filter abstraction
    def filter(self, obj):
        build = obj
        params = self.get_params()
        for k, v in params.items():
            build = [c for c in build if c[k] == v]
        return build

    def list_courses(self):
        return self.filter(courses)

    def list_books(self):
        return self.filter(books)

    def list_parts(self):
        return self.filter(parts)

    def list_chapters(self):
        return self.filter(chapters)

    def json_response(self, data: str):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def file_response(self, data: bytes):
        self.send_response(200)
        self.send_header("Content-type", "binary/octet-stream")
        self.send_header("Content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        # base path
        if self.path == "/":
            self.json_response("")
        elif self.path.startswith(COURSE_API):
            data = self.dump(self.list_courses())
            self.json_response(data)
        elif self.path.startswith("/handout_url.tgz"):
            self.file_response(b"handout_url")
        elif self.path.startswith("/api/courses/0/codelabs/0/attached_file_urls/"):
            data = self.dump({
                "handout_url": f"http://{ADDR}:{PORT}/handout_url.tgz",
            })
            self.json_response(data)
        elif self.path.startswith("/api/courses/0/codelabs/"):
            data = self.dump(self.filter([lab for lab in codelabs if lab["course"] == "0"]))
            self.json_response(data)
        elif self.path.startswith("/api/courses/1/codelabs/"):
            data = self.dump(self.filter([lab for lab in codelabs if lab["course"] == "1"]))
            self.json_response(data)
        elif self.path.startswith(BOOK_API):
            data = self.dump(self.list_books())
            self.json_response(data)
        elif self.path.startswith(PARTS_API):
            data = self.dump(self.list_parts())
            self.json_response(data)
        elif self.path.startswith(CHAPTERS_API):
            data = self.dump(self.list_chapters())
            self.json_response(data)
        else:
            print("GOT THIS URL AND IM ANGRY", self.path)
            self.send_response(200)
            self.end_headers()

    def do_PATCH(self):
        if self.path.startswith("/api/courses/0/codelabs/0"):
            success = True
            # HEADERS are now in dict/json style container
            _, pdict = cgi.parse_header(self.headers["content-type"])

            # boundary data needs to be encoded in a binary format
            pdict["boundary"] = bytes(pdict["boundary"], "utf-8")
            pdict["CONTENT-LENGTH"] = self.headers["Content-Length"]
            fields = cgi.parse_multipart(self.rfile, pdict)
            # assert that autograde-tar, autograde-makefile,
            # writeup and handout are in the files list.
            success = all(
                [
                    success,
                    "autograder-makefile" in fields,
                    "autograder-tar" in fields,
                    "handout" in fields,
                ]
            )
            if success:
                self.send_response(200)
            else:
                self.send_response(400)
            self.send_header("Content-length", "0")
        else:
            self.send_response(200)
            self.send_header("Content-length", "0")
        self.end_headers()

    def do_POST(self):
        # Handle the login behavior
        if self.path.startswith(LOGIN_URL):
            data = self.dump({"key": "test"})
            self.json_response(data)
        # handle submitting an assignment to course 0
        elif self.path.startswith("/api/courses/0/codelabs/0/submissions/create_and_submit/"):
            success = True
            # assert that submission tar is indeed in the request files
            self.rfile.readline()
            line = str(self.rfile.readline())

            # depending on the upload type of the homework, check that
            # the appropriate tag is in the header
            hws = [chw for chw in codelabs if chw["id"] == "0"]
            success = len(hws) == 1 and success
            success = 'name="submission_tar"' in line and success

            if success:
                self.send_response(200)
            else:
                self.send_response(400)
            self.send_header("Content-length", "0")
        # support book management only on course 0
        elif self.path.startswith("/course/0/books/manage_book/"):
            success = True

            ctype, pdict = cgi.parse_header(self.headers["content-type"])

            if ctype == "multipart/form-data":
                pdict["boundary"] = bytes(pdict["boundary"], "utf-8")
                pdict["CONTENT-LENGTH"] = self.headers["Content-Length"]
                params = cgi.parse_multipart(self.rfile, pdict)
                params = dict([(k, v[0]) for k, v in params.items()])
            else:
                params = self.post_params()

            if params["kind"] == "create chapter":
                # assert part_pk, rank, label, and title are present
                success = all(["part_pk" in params, "rank" in params, "title" in params, "label" in params, success])
            elif params["kind"] == "create part":
                # assert lable, title and rank are present
                success = all(["rank" in params, "title" in params, "label" in params, success])
            elif params["kind"] == "upload content":
                success = True
                if "input_file_pdf" in params:
                    success = success and "video_url_pdf" in params
                elif "input_file_slide" in params:
                    success = success and "video_url_slide" in params
                elif "input_file_xml" in params:
                    success = success and "input_file_xml_pdf" in params
                    # It doesn't seem like we can do any verification of
                    # file lists on the server end...
                    # TODO (rohany): see if this is possible!
                else:
                    # None of the files are in here!
                    success = False
            elif params["kind"] == "release" or params["kind"] == "unrelease":
                success = "chapter_pk" in params and success
            else:
                success = False
            if success:
                self.send_response(200)
            else:
                self.send_response(400)
            self.send_header("Content-length", "0")
        else:
            self.send_response(200)
            self.send_header("Content-length", "0")
        self.end_headers()

    # silence log messages.
    def log_message(self, format, *args):
        return


# run the unit tests
if __name__ == "__main__":
    server_address = (ADDR, PORT)
    httpd = HTTPServer(server_address, DiderotHTTPHandler)
    httpd.serve_forever()
