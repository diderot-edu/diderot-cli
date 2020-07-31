#!/usr/bin/env python3

import atexit
import http
import json
import logging
import subprocess
import sys
import threading
import time
import unittest
import urllib
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import StringIO
from urllib.parse import urlparse

import requests

from standalone import DiderotAdmin, DiderotUser

log = logging.getLogger("TESTLOG")
ADDR = "127.0.0.1"
PORT = 8080
SERVURL = "http://{}:{}".format(ADDR, PORT)

# Define some sample data.
# TODO (rohany): maybe move this into its own file
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
        "is_booklet": False,
    },
    {
        "label": "TestBook2",
        "course": "0",
        "course__label": "TestCourse0",
        "title": "TestBook2",
        "version": "1",
        "id": "1",
        "is_locked": False,
        "is_booklet": True,
    },
    {
        "label": "TestBook3",
        "course": "1",
        "course__label": "TestCourse1",
        "title": "TestBook3",
        "version": "1",
        "id": "2",
        "is_locked": False,
        "is_booklet": False,
    },
    {
        "label": "TestBook4",
        "course": "1",
        "course__label": "TestCourse1",
        "title": "TestBook4",
        "version": "1",
        "id": "3",
        "is_locked": False,
        "is_booklet": False,
    },
]

# make parts for only one course.
parts = [
    {"id": "0", "label": "TestPart1", "book": "0", "book__id": "0", "title": "TestPart1", "rank": "1",},
    {"id": "1", "label": "TestPart2", "book": "0", "book__id": "0", "title": "TestPart2", "rank": "2",},
    {"id": "2", "label": "TestPart3", "book": "1", "book__id": "1", "title": "TestPart3", "rank": "1",},
]

chapters = [
    {
        "id": "0",
        "label": "TestChapter1",
        "book": "0",
        "book__id": "0",
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
        "upload_errors": "",
        "upload_warnings": "",
        "title": "TestChapter2",
        "rank": "2",
        "course__label": "TestCourse0",
        "course__id": "0",
    },
]


# Capture stdout from the function calls.
class Capture(list):
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self

    def __exit__(self, *args):
        self.append(self._stringio.getvalue())
        del self._stringio  # free up some memory
        sys.stdout = self._stdout


# Helper functions for creating a client
def cleanOutput(res):
    return res.replace("\n", " ")


def runUserCmd(cmd):
    baseCmd = "--url {} --username test --password test".format(SERVURL)
    fullCmd = baseCmd + " " + cmd
    with Capture() as output:
        try:
            DiderotUser(line=fullCmd).dispatch()
        except SystemExit:
            pass
    return cleanOutput(output[0])


def runAdminCmd(cmd):
    baseCmd = "--url {} --username test --password test".format(SERVURL)
    fullCmd = baseCmd + " " + cmd
    with Capture() as output:
        try:
            DiderotAdmin(line=fullCmd, sleep_time=0).dispatch()
        except SystemExit:
            pass
    return cleanOutput(output[0])


# Define the unit test classes
class TestDiderotUserCLI(unittest.TestCase):
    # TODO (rohany): add a test for credentials

    def test_list_courses(self):
        output = runUserCmd("list_courses").split()
        self.assertTrue(len(courses) == len(output))
        for c in courses:
            self.assertTrue(c["label"] in output)

    def test_list_assignments(self):
        # Test invalid course label.
        output = runUserCmd("list_assignments fakelabel")
        self.assertTrue("The requested course label does not exist." in output)

        # Test that assignment data is correct when switching on course.
        for c in ["TestCourse0", "TestCourse1"]:
            output = runUserCmd("list_assignments {}".format(c))
            correct_hws = [chw for chw in codelabs if chw["course__label"] == c]
            self.assertTrue(len(correct_hws) == len(output.split()))
            for hw in correct_hws:
                self.assertTrue(hw["name"] in output)

    def test_download_assignment(self):
        # Test invalid course label.
        output = runUserCmd("download_assignment fakelabel fakehw")
        self.assertTrue("The requested course label does not exist." in output)

        # Test invalid homework name.
        output = runUserCmd("download_assignment TestCourse0 fakehw")
        self.assertTrue("Invalid homework name." in output)

        # Expect success with valid hw name and course name.
        output = runUserCmd("download_assignment TestCourse0 TestHW1")
        self.assertTrue("Successfully downloaded assignment." in output)

    def test_submit_assignment(self):
        # Test invalid course label.
        output = runUserCmd("submit_assignment fakelabel fakehw fakepath")
        self.assertTrue("The requested course label does not exist." in output)
        self.assertTrue("Something went wrong." in output)

        # Test invalid homework name.
        output = runUserCmd("submit_assignment TestCourse0 fakehw fakepath")
        self.assertTrue("Invalid homework name." in output)
        self.assertTrue("Something went wrong." in output)

        # Test invalid input file name.
        output = runUserCmd("submit_assignment TestCourse0 TestHW1 fakepath")
        self.assertTrue("Input file does not exist." in output)
        self.assertTrue("Something went wrong." in output)

        # Expect successful execution here!
        output = runUserCmd("submit_assignment TestCourse0 TestHW1 testdata/test_handin.tar")
        self.assertTrue("Assignment submitted successfully." in output)


class TestDiderotAdminCLI(unittest.TestCase):
    def test_create_chapter(self):
        # Test invalid course label.
        output = runAdminCmd("create_chapter fakecourse fakebook --number 1")
        self.assertTrue("The requested course label does not exist." in output)

        # Test invalid book label.
        output = runAdminCmd("create_chapter TestCourse0 fakebook --number 1")
        self.assertTrue("Input book not found." in output)

        # Test error is raised when book is not a booklet and parts is not provided.
        output = runAdminCmd("create_chapter TestCourse0 TestBook1 --number 1")
        self.assertTrue("--part must be set." in output)

        # Test error when input part is invalid.
        output = runAdminCmd("create_chapter TestCourse0 TestBook1 --part 3 --number 1")
        self.assertTrue("Input part not found." in output)

        # Test error when chapter exists.
        output = runAdminCmd("create_chapter TestCourse0 TestBook1 --part 1 --number 1")
        self.assertTrue("Existing chapter for" in output)

        # Expect a successful response.
        output = runAdminCmd(
            "create_chapter TestCourse0 TestBook1 --part 1 --number 3 --title TestChapter3 --label TestChapter3"
        )
        self.assertTrue("Successfully created chapter." in output)

        # Expect successful response for non booklets.
        output = runAdminCmd(
            "create_chapter TestCourse0 TestBook2 --number 3 --title TestChapter3 --label TestChapter3"
        )
        self.assertTrue("Successfully created chapter." in output)

    def test_create_part(self):
        # Test an invalid course label.
        output = runAdminCmd("create_part fakecourse fakebook NewTestPart 1")
        self.assertTrue("The requested course label does not exist." in output)

        # Test an invalid book label.
        output = runAdminCmd("create_part TestCourse0 fakebook NewTestPart 1")
        self.assertTrue("Input book not found." in output)

        # Test error when part exists.
        output = runAdminCmd("create_part TestCourse0 TestBook1 NewTestPart 1")
        self.assertTrue("Existing part for Course" in output)

        # Test error on a booklet.
        output = runAdminCmd("create_part TestCourse0 TestBook2 NewTestPart 3")
        self.assertTrue("Part creation is disallowed on booklets." in output)

        # Expect successful response.
        output = runAdminCmd("create_part TestCourse0 TestBook1 NewTestPart 3 --label NewTestPart")
        self.assertTrue("Successfully created part." in output)

    def test_list_books(self):
        # With no course provided, expect an error.
        output = runAdminCmd("list_books")
        self.assertTrue("A course label is required if not listing all books." in output)

        # Test with invalid course label.
        output = runAdminCmd("list_books fakecourse")
        self.assertTrue("The requested course label does not exist." in output)

        # Test with a valid input course label.
        for c in ["TestCourse0", "TestCourse1"]:
            output = runAdminCmd("list_books {}".format(c))
            correct_books = [b for b in books if b["course__label"] == c]
            self.assertTrue(len(correct_books) == len(output.split()))
            for b in correct_books:
                self.assertTrue(b["label"] in output)

        # Test the --all flag.
        output = runAdminCmd("list_books --all")
        self.assertTrue(len(output.split()) == len(books))
        for b in books:
            self.assertTrue(b["label"] in output)

    def test_list_chapters(self):
        # Test invalid course label.
        output = runAdminCmd("list_chapters fakecourse fakebook")
        self.assertTrue("The requested course label does not exist." in output)

        # Test invalid book label.
        output = runAdminCmd("list_chapters TestCourse0 fakebook")
        self.assertTrue("Input book not found." in output)

        # Test that we get expected results with a valid book.
        output = runAdminCmd("list_chapters TestCourse0 TestBook1")
        # We multiply by 2 because we include the parts rank in the output.
        self.assertTrue(2 * len(chapters) == len(output.split()))
        for c in chapters:
            s = "{}. {}".format(c["rank"], c["title"])
            self.assertTrue(s in output)

        # Test that we don't get any results with a book with no chapters.
        output = runAdminCmd("list_chapters TestCourse0 TestBook2")
        self.assertTrue(len(output) == 0)

    def test_list_parts(self):
        # Test invalid course label.
        output = runAdminCmd("list_parts fakecourse fakebook")
        self.assertTrue("The requested course label does not exist." in output)

        # Test invalid book label.
        output = runAdminCmd("list_parts TestCourse0 fakebook")
        self.assertTrue("Input book not found." in output)

        # Test that we get expected results with a valid book.
        output = runAdminCmd("list_parts TestCourse0 TestBook1")
        correct_parts = [p for p in parts if p["book__id"] == "0"]
        # We multiply by 2 because we include the parts rank in the output.
        self.assertTrue(2 * len(correct_parts) == len(output.split()))
        for p in correct_parts:
            s = "{}. {}".format(p["rank"], p["title"])
            self.assertTrue(s in output)

        # Test that we don't get any results with a book with no parts.
        output = runAdminCmd("list_parts TestCourse1 TestBook3")
        self.assertTrue(len(output) == 0)

    def test_release_unrelease_chapter(self):
        # Test invalid course label.
        output = runAdminCmd("release_chapter fakecourse fakebook --chapter_number 10")
        self.assertTrue("The requested course label does not exist." in output)
        output = runAdminCmd("unrelease_chapter fakecourse fakebook --chapter_number 10")
        self.assertTrue("The requested course label does not exist." in output)

        # Test invalid book.
        output = runAdminCmd("release_chapter TestCourse0 fakebook --chapter_number 10")
        self.assertTrue("Input book not found." in output)
        output = runAdminCmd("unrelease_chapter TestCourse0 fakebook --chapter_number 10")
        self.assertTrue("Input book not found." in output)

        # Test invalid chapter number.
        output = runAdminCmd("release_chapter TestCourse0 TestBook1 --chapter_number 10")
        self.assertTrue("Input chapter not found." in output)
        output = runAdminCmd("unrelease_chapter TestCourse0 TestBook1 --chapter_number 10")
        self.assertTrue("Input chapter not found." in output)

        # Test invalid chapter label.
        output = runAdminCmd("release_chapter TestCourse0 TestBook1 --chapter_label fakelabel")
        self.assertTrue("Input chapter not found." in output)
        output = runAdminCmd("unrelease_chapter TestCourse0 TestBook1 --chapter_label fakelabel")
        self.assertTrue("Input chapter not found." in output)

        # Test success in releasing chapter.
        output = runAdminCmd("release_chapter TestCourse0 TestBook1 --chapter_label TestChapter1")
        self.assertTrue("Success releasing chapter." in output)
        output = runAdminCmd("unrelease_chapter TestCourse0 TestBook1 --chapter_label TestChapter1")
        self.assertTrue("Success unreleasing chapter." in output)

        output = runAdminCmd("release_chapter TestCourse0 TestBook1 --chapter_number 1")
        self.assertTrue("Success releasing chapter." in output)
        output = runAdminCmd("unrelease_chapter TestCourse0 TestBook1 --chapter_number 1")
        self.assertTrue("Success unreleasing chapter." in output)

    def test_update_assignment(self):
        # Test invalid course label.
        output = runAdminCmd("update_assignment fakecourse fakehw")
        self.assertTrue("The requested course label does not exist." in output)
        self.assertTrue("Uploading files failed. Try using the Web UI." in output)

        # Test invalid homework name.
        output = runAdminCmd("update_assignment TestCourse0 fakehw")
        self.assertTrue("Invalid homework name." in output)
        self.assertTrue("Uploading files failed. Try using the Web UI." in output)

        # Expect success.
        output = runAdminCmd(
            "update_assignment TestCourse0 TestHW1 --autograde-tar testdata/autograde.tar\
             --autograde-makefile testdata/autograde-Makefile \
             --handout testdata/handout.tar"
        )
        self.assertTrue("Success uploading files." in output)

    def test_upload_chapter(self):
        # Test invalid course label.
        output = runAdminCmd("upload_chapter fakecourse fakebook --chapter_number 10 --pdf fakepdf")
        self.assertTrue("The requested course label does not exist." in output)

        # Test invalid book.
        output = runAdminCmd("upload_chapter TestCourse0 fakebook --chapter_number 10 --pdf fakepdf")
        self.assertTrue("Input book not found." in output)

        # Test invalid chapter number.
        output = runAdminCmd("upload_chapter TestCourse0 TestBook1 --chapter_number 10 --pdf fakepdf")
        self.assertTrue("Input chapter not found." in output)

        # Test invalid chapter label.
        output = runAdminCmd("upload_chapter TestCourse0 TestBook1 --chapter_label fakelabel --pdf fakepdf")
        self.assertTrue("Input chapter not found." in output)

        # Test acceptance / not acceptance of certain argument combinations.
        output = runAdminCmd(
            "upload_chapter TestCourse0 TestBook1 --chapter_number 1 --xml dummy.xml --video_url fakeurl"
        )
        self.assertTrue("Cannot use --video_url with xml uploads." in output)

        output = runAdminCmd("upload_chapter TestCourse0 TestBook1 --chapter_number 1 --pdf dummy.pdf --attach dummy")
        self.assertTrue("Cannot use --attach if not uploading xml/mlx." in output)

        output = runAdminCmd(
            "upload_chapter TestCourse0 TestBook1 --chapter_number 1 --slides dummy.pdf --attach dummy"
        )
        self.assertTrue("Cannot use --attach if not uploading xml/mlx." in output)

        # Test that pdf, slides, xml work.

        # Pdf upload test.
        # Expect an error if used not on a pdf.
        output = runAdminCmd(
            "upload_chapter TestCourse0 TestBook1 --chapter_number 1 --pdf testdata/book.xml --video_url fakeurl"
        )
        self.assertTrue("PDF argument must be a PDF file." in output)

        output = runAdminCmd(
            "upload_chapter TestCourse0 TestBook1 --chapter_number 1 --pdf testdata/chapter.pdf --video_url fakeurl"
        )
        self.assertTrue("Chapter uploaded successfully." in output)

        # Slides upload test.
        # Expect an error if used not on a pdf.
        output = runAdminCmd(
            "upload_chapter TestCourse0 TestBook1 --chapter_number 1 --slides testdata/book.xml --video_url fakeurl"
        )
        self.assertTrue("Slides argument must be a PDF file." in output)

        output = runAdminCmd(
            "upload_chapter TestCourse0 TestBook1 --chapter_number 1 --slides testdata/slides.pdf --video_url fakeurl"
        )
        self.assertTrue("Chapter uploaded successfully." in output)

        # Xml/mlx upload test.
        output = runAdminCmd(
            "upload_chapter TestCourse0 TestBook1 --chapter_number 1 --xml testdata/book.xml --xml_pdf testdata/book.pdf"
        )
        self.assertTrue("Chapter uploaded successfully." in output)

        output = runAdminCmd(
            "upload_chapter TestCourse0 TestBook1 --chapter_label TestChapter1 --xml testdata/book.xml --xml_pdf testdata/book.pdf"
        )
        self.assertTrue("Chapter uploaded successfully." in output)

        output = runAdminCmd(
            "upload_chapter TestCourse0 TestBook1 --chapter_number 1 --xml testdata/book.mlx --xml_pdf testdata/book.pdf"
        )
        self.assertTrue("Chapter uploaded successfully." in output)

        output = runAdminCmd(
            "upload_chapter TestCourse0 TestBook1 --chapter_label TestChapter1 --xml testdata/book.mlx --xml_pdf testdata/book.pdf"
        )
        self.assertTrue("Chapter uploaded successfully." in output)

        # Test folder.
        output = runAdminCmd(
            "upload_chapter TestCourse0 TestBook1 --chapter_number 1 --xml testdata/book.mlx --xml_pdf testdata/book.pdf --attach testdata/images/"
        )
        self.assertTrue("Uploading file: test1.png" in output)
        self.assertTrue("Uploading file: test2.png" in output)
        self.assertTrue("Chapter uploaded successfully." in output)

        # Test glob.
        output = runAdminCmd(
            "upload_chapter TestCourse0 TestBook1 --chapter_number 1 --xml testdata/book.mlx --xml_pdf testdata/book.pdf --attach testdata/images/*"
        )
        self.assertTrue("Uploading file: test1.png" in output)
        self.assertTrue("Uploading file: test2.png" in output)
        self.assertTrue("Chapter uploaded successfully." in output)

        # Test file list.
        output = runAdminCmd(
            "upload_chapter TestCourse0 TestBook1 --chapter_number 1 --xml testdata/book.mlx --xml_pdf testdata/book.pdf --attach testdata/images/test1.png testdata/images/test2.png"
        )
        self.assertTrue("Uploading file: test1.png" in output)
        self.assertTrue("Uploading file: test2.png" in output)
        self.assertTrue("Chapter uploaded successfully." in output)


# Run the unit tests.
if __name__ == "__main__":
    # Start the server in a subprocess.
    print("Starting webserver.")
    server = subprocess.Popen(["python3", "test_server.py"])
    time.sleep(1)

    def killServer():
        server.kill()

    atexit.register(killServer)
    logging.basicConfig(stream=sys.stderr)
    logging.getLogger("TESTLOG").setLevel(logging.DEBUG)
    print("Beginning tests.")
    unittest.main()
