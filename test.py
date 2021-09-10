import logging
import shlex
import subprocess
import sys
import time
import traceback
import unittest

from io import StringIO
from click.testing import CliRunner, Result

from diderot_cli.commands import diderot
from diderot_cli.constants import SERVURL
from test_server import books, chapters, codelabs, courses, parts

log = logging.getLogger("TESTLOG")

def run_cmd(runner: CliRunner, cmd, user: str):
    base_cmd = f"{user} --url {SERVURL} --username test --password test --no-debug"
    full_cmd = f"{base_cmd} {cmd}"

    result = runner.invoke(diderot, full_cmd)

    return result

class Base(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    def assert_successful_execution(self):
        if self.result.exit_code != 0:
            traceback.print_tb(self.result.exc_info[2])
        self.assertEqual(self.result.exit_code, 0)

    def assert_unsuccessful_execution(self, exit_code=1):
        self.assertEqual(self.result.exit_code, exit_code)

    def run_admin_cmd(self, cmd):
        self.result = run_cmd(self.runner, cmd, "admin")

    def run_user_cmd(self, cmd):
        self.result = run_cmd(self.runner, cmd, "student")

    def assert_in_output(self, message):
        self.assertTrue(message in self.result.output, self.result.output)

# Define the unit test classes
class TestDiderotUserCLI(Base):
    # TODO (rohany): add a test for credentials
    def test_list_courses(self):
        self.run_user_cmd("list-courses")
        self.assert_successful_execution()

        # 6 extra elements in output for labels (splitted): "Active courses", "Inactive courses", "public courses"
        output = shlex.split(self.result.output)
        self.assertEqual(len(courses), len(output))
        for c in courses:
            self.assert_in_output(c["label"])

    def test_list_assignments(self):
        # Test invalid course label.
        self.run_user_cmd("list-assignments fakelabel")

        self.assert_unsuccessful_execution()
        self.assert_in_output("The requested course label does not exist.")

        # Test that assignment data is correct when switching on course.
        for c in ["TestCourse0", "TestCourse1"]:
            self.run_user_cmd(f"list-assignments {c}")

            self.assert_successful_execution()

            correct_hws = [chw for chw in codelabs if chw["course__label"] == c]
            self.assertTrue(len(correct_hws) == len(shlex.split(self.result.output)))
            for hw in correct_hws:
                self.assert_in_output(hw["name"])

    def test_download_assignment(self):
        # Test invalid course label.
        self.run_user_cmd("download-assignment fakelabel fakehw")

        self.assert_unsuccessful_execution()
        self.assert_in_output("The requested course label does not exist.")

        # Test invalid homework name.
        self.run_user_cmd("download-assignment TestCourse0 fakehw")

        self.assert_unsuccessful_execution()
        self.assert_in_output("Invalid homework name.")

        # Expect success with valid hw name and course name.
        with self.runner.isolated_filesystem():
            self.run_user_cmd("download-assignment TestCourse0 TestHW1")

        self.assert_successful_execution()
        self.assert_in_output("Successfully downloaded assignment.")

    def test_submit_assignment(self):
        # Test invalid course label.
        self.run_user_cmd("submit-assignment fakelabel fakehw testdata/test_handin.tar")

        self.assert_unsuccessful_execution()
        self.assert_in_output("The requested course label does not exist.")
        self.assert_in_output("You might not be a member")

        # Test invalid homework name.
        self.run_user_cmd("submit-assignment TestCourse0 fakehw testdata/test_handin.tar")

        self.assert_unsuccessful_execution()
        self.assert_in_output("Invalid homework name.")

        # Test invalid input file name.
        self.run_user_cmd("submit-assignment TestCourse0 TestHW1 testdata/invalid.tar")

        self.assert_unsuccessful_execution(exit_code=2)
        self.assert_in_output("Path 'testdata/invalid.tar' does not exist.")

        # Expect successful execution here!
        self.run_user_cmd("submit-assignment TestCourse0 TestHW1 testdata/test_handin.tar")

        self.assert_successful_execution()
        self.assert_in_output("Assignment submitted successfully.")


class TestDiderotAdminCLI(Base):
    def test_create_chapter(self):
        # Test invalid course label.
        self.run_admin_cmd("create-chapter fakecourse fakebook --chapter-number 1")

        self.assert_unsuccessful_execution()
        self.assert_in_output("The requested course label does not exist.")

        # Test invalid book label.
        self.run_admin_cmd("create-chapter TestCourse0 fakebook --chapter-number 1")

        self.assert_unsuccessful_execution()
        self.assert_in_output("Input book not found.")

        # Test error is raised when book is not a booklet and parts is not provided.
        self.run_admin_cmd("create-chapter TestCourse0 TestBook1 --chapter-number 1")

        self.assert_unsuccessful_execution()
        self.assert_in_output("--part-number must be set.")

        # Test error when input part is invalid.
        self.run_admin_cmd("create-chapter TestCourse0 TestBook1 --part-number 3 --chapter-number 1")

        self.assert_unsuccessful_execution()
        self.assert_in_output("Input part not found.")

        # Test error when chapter exists.
        self.run_admin_cmd("create-chapter TestCourse0 TestBook1 --part-number 1 --chapter-number 1")

        self.assert_unsuccessful_execution()
        self.assert_in_output("Existing chapter for")

        # Expect a successful response.
        self.run_admin_cmd(
            "create-chapter TestCourse0 TestBook1 --part-number 1 --chapter-number 3 --title TestChapter3 --chapter-label TestChapter3"
        )
        self.assert_successful_execution()
        self.assert_in_output("Successfully created chapter.")

        # Expect successful response for non booklets.
        self.run_admin_cmd(
            "create-chapter TestCourse0 TestBook2 --part-number 1 --chapter-number 3 --title TestChapter3 --chapter-label TestChapter3"
        )
        self.assert_successful_execution()
        self.assert_in_output("Successfully created chapter.")

    def test_create_part(self):
        # Test an invalid course label.
        self.run_admin_cmd("create-part fakecourse fakebook NewTestPart --chapter-number 1")

        self.assert_unsuccessful_execution()
        self.assert_in_output("The requested course label does not exist.")

        # Test an invalid book label.
        self.run_admin_cmd("create-part TestCourse0 fakebook NewTestPart --chapter-number 1")

        self.assert_unsuccessful_execution()
        self.assert_in_output("Input book not found.")

        # Test error when part exists.
        self.run_admin_cmd("create-part TestCourse0 TestBook1 NewTestPart --chapter-number 1")

        self.assert_unsuccessful_execution()
        self.assert_in_output("Existing part for Course")

        # Expect successful response.
        self.run_admin_cmd("create-part TestCourse0 TestBook1 NewTestPart --chapter-number 3 --chapter-label NewTestPart")

        self.assert_successful_execution()
        self.assert_in_output("Successfully created part.")

    def test_list_books(self):
        # With no course provided, expect an error.
        self.run_admin_cmd("list-books")

        self.assert_unsuccessful_execution()
        self.assert_in_output("A course label is required if not listing all books.")

        # Test with invalid course label.
        self.run_admin_cmd("list-books fakecourse")

        self.assert_unsuccessful_execution()
        self.assert_in_output("The requested course label does not exist.")

        # Test with a valid input course label.
        for c in ["TestCourse0", "TestCourse1"]:
            self.run_admin_cmd("list-books {}".format(c))

            self.assert_successful_execution()

            correct_books = [b for b in books if b["course__label"] == c]
            self.assertTrue(len(correct_books) == len(shlex.split(self.result.output)))
            for b in correct_books:
                self.assert_in_output(b["label"])

        # Test the --all flag.
        self.run_admin_cmd("list-books --all")

        self.assert_successful_execution()
        self.assertTrue(len(shlex.split(self.result.output)) == len(books))

        for b in books:
            self.assert_in_output(b["label"])

    def test_list_chapters(self):
        # Test invalid course label.
        self.run_admin_cmd("list-chapters fakecourse fakebook")

        self.assert_unsuccessful_execution()
        self.assert_in_output("The requested course label does not exist.")

        # Test invalid book label.
        self.run_admin_cmd("list-chapters TestCourse0 fakebook")

        self.assert_unsuccessful_execution()
        self.assert_in_output("Input book not found.")

        # Test that we get expected results with a valid book.
        self.run_admin_cmd("list-chapters TestCourse0 TestBook1")

        self.assert_successful_execution()

        # We multiply by 2 because we include the parts rank in the output.
        self.assertTrue(2 * len(chapters) == len(shlex.split(self.result.output)))
        for c in chapters:
            s = "{}. {}".format(c["rank"], c["title"])
            self.assert_in_output(s)

        # Test that we don't get any results with a book with no chapters.
        self.run_admin_cmd("list-chapters TestCourse0 TestBook2")

        self.assert_successful_execution()
        self.assertTrue(len(self.result.output) == 0)

    def test_list_parts(self):
        # Test invalid course label.
        self.run_admin_cmd("list-parts fakecourse fakebook")

        self.assert_unsuccessful_execution()
        self.assert_in_output("The requested course label does not exist.")

        # Test invalid book label.
        self.run_admin_cmd("list-parts TestCourse0 fakebook")

        self.assert_unsuccessful_execution()
        self.assert_in_output("Input book not found.")

        # Test that we get expected results with a valid book.
        self.run_admin_cmd("list-parts TestCourse0 TestBook1")

        self.assert_successful_execution()

        correct_parts = [p for p in parts if p["book__id"] == "0"]
        # We multiply by 2 because we include the parts rank in the output.
        self.assertTrue(2 * len(correct_parts) == len(shlex.split(self.result.output)))
        for p in correct_parts:
            s = "{}. {}".format(p["rank"], p["title"])
            self.assert_in_output(s)

        # Test that we don't get any results with a book with no parts.
        self.run_admin_cmd("list-parts TestCourse1 TestBook3")

        self.assert_successful_execution()
        self.assertTrue(len(self.result.output) == 0)

    def test_publish_retract_chapter(self):
        # Test invalid course label.
        self.run_admin_cmd("publish-chapter fakecourse fakebook --chapter-number 10")

        self.assert_unsuccessful_execution()
        self.assert_in_output("The requested course label does not exist.")

        self.run_admin_cmd("retract-chapter fakecourse fakebook --chapter-number 10")

        self.assert_unsuccessful_execution()
        self.assert_in_output("The requested course label does not exist.")

        # Test invalid book.
        self.run_admin_cmd("publish-chapter TestCourse0 fakebook --chapter-number 10")

        self.assert_unsuccessful_execution()
        self.assert_in_output("Input book not found.")

        self.run_admin_cmd("retract-chapter TestCourse0 fakebook --chapter-number 10")

        self.assert_unsuccessful_execution()
        self.assert_in_output("Input book not found.")

        # Test invalid chapter number.
        self.run_admin_cmd("publish-chapter TestCourse0 TestBook1 --chapter-number 10")

        self.assert_unsuccessful_execution()
        self.assert_in_output("Input chapter not found.")

        self.run_admin_cmd("retract-chapter TestCourse0 TestBook1 --chapter-number 10")

        self.assert_unsuccessful_execution()
        self.assert_in_output("Input chapter not found.")

        # Test invalid chapter label.
        self.run_admin_cmd("publish-chapter TestCourse0 TestBook1 --chapter-label fakelabel")

        self.assert_unsuccessful_execution()
        self.assert_in_output("Input chapter not found.")

        self.run_admin_cmd("retract-chapter TestCourse0 TestBook1 --chapter-label fakelabel")

        self.assert_unsuccessful_execution()
        self.assert_in_output("Input chapter not found.")

        # Test success in releasing chapter.
        self.run_admin_cmd("publish-chapter TestCourse0 TestBook1 --chapter-label TestChapter1")

        self.assert_successful_execution()
        self.assert_in_output("Success publishing chapter.")

        self.run_admin_cmd("retract-chapter TestCourse0 TestBook1 --chapter-label TestChapter1")

        self.assert_successful_execution()
        self.assert_in_output("Success retracting chapter.")

        self.run_admin_cmd("publish-chapter TestCourse0 TestBook1 --chapter-number 1")

        self.assert_successful_execution()
        self.assert_in_output("Success publishing chapter.")

        self.run_admin_cmd("retract-chapter TestCourse0 TestBook1 --chapter-number 1")

        self.assert_successful_execution()
        self.assert_in_output("Success retracting chapter.")

    def test_update_assignment(self):
        # Test invalid course label.
        self.run_admin_cmd("update-assignment fakecourse fakehw")

        self.assert_unsuccessful_execution()
        self.assert_in_output("The requested course label does not exist.")

        # Test invalid homework name.
        self.run_admin_cmd("update-assignment TestCourse0 fakehw")

        self.assert_unsuccessful_execution()
        self.assert_in_output("Invalid homework name.")

        # Expect success.
        self.run_admin_cmd(
            "update-assignment TestCourse0 TestHW1 --autograde-tar testdata/autograde.tar\
             --autograde-makefile testdata/autograde-Makefile \
             --handout testdata/handout.tar"
        )
        self.assert_successful_execution()
        self.assert_in_output("Success uploading files.")

    def test_upload_chapter(self):
        # Test invalid course label.
        self.run_admin_cmd("upload-chapter fakecourse fakebook --chapter-number 10 --pdf testdata/chapter.pdf")

        self.assert_unsuccessful_execution()
        self.assert_in_output("The requested course label does not exist.")

        # Test invalid book.
        self.run_admin_cmd("upload-chapter TestCourse0 fakebook --chapter-number 10 --pdf testdata/chapter.pdf")

        self.assert_unsuccessful_execution()
        self.assert_in_output("Input book not found.")

        # Test invalid chapter number.
        self.run_admin_cmd("upload-chapter TestCourse0 TestBook1 --chapter-number 10 --pdf testdata/chapter.pdf")

        self.assert_unsuccessful_execution()
        self.assert_in_output("Input chapter not found.")

        # Test invalid chapter label.
        self.run_admin_cmd("upload-chapter TestCourse0 TestBook1 --chapter-label fakelabel --pdf testdata/chapter.pdf")

        self.assert_unsuccessful_execution()
        self.assert_in_output("Input chapter not found.")

        # Pdf upload test.
        # Expect an error if used not on a pdf.
        self.run_admin_cmd(
            "upload-chapter TestCourse0 TestBook1 --chapter-number 1 --pdf testdata/book.xml --video-url fakeurl"
        )
        self.assert_in_output("PDF argument must be a PDF file.")

        self.run_admin_cmd(
            "upload-chapter TestCourse0 TestBook1 --chapter-number 1 --pdf testdata/chapter.pdf --video-url fakeurl"
        )
        self.assert_successful_execution()
        self.assert_in_output("Chapter uploaded successfully.")

        # Xml/mlx upload test.
        self.run_admin_cmd(
            "upload-chapter TestCourse0 TestBook1 --chapter-number 1 --xml testdata/book.xml --xml-pdf testdata/book.pdf"
        )
        self.assert_successful_execution()
        self.assert_in_output("Chapter uploaded successfully.")

        self.run_admin_cmd(
            "upload-chapter TestCourse0 TestBook1 --chapter-label TestChapter1 --xml testdata/book.xml --xml-pdf testdata/book.pdf"
        )
        self.assert_successful_execution()
        self.assert_in_output("Chapter uploaded successfully.")

        self.run_admin_cmd(
            "upload-chapter TestCourse0 TestBook1 --chapter-number 1 --xml testdata/book.mlx --xml-pdf testdata/book.pdf"
        )
        self.assert_successful_execution()
        self.assert_in_output("Chapter uploaded successfully.")

        self.run_admin_cmd(
            "upload-chapter TestCourse0 TestBook1 --chapter-label TestChapter1 --xml testdata/book.mlx --xml-pdf testdata/book.pdf"
        )
        self.assert_successful_execution()
        self.assert_in_output("Chapter uploaded successfully.")

        # Test folder.
        self.run_admin_cmd(
            "upload-chapter TestCourse0 TestBook1 --chapter-number 1 --xml testdata/book.mlx --xml-pdf testdata/book.pdf --attach testdata/images/"
        )
        self.assert_successful_execution()
        self.assert_in_output("Uploading file: test1.png")
        self.assert_in_output("Uploading file: test2.png")
        self.assert_in_output("Chapter uploaded successfully.")

        # Test file list.
        self.run_admin_cmd(
            "upload-chapter TestCourse0 TestBook1 --chapter-number 1 --xml testdata/book.mlx --xml-pdf testdata/book.pdf --attach testdata/images/test1.png --attach testdata/images/test2.png"
        )
        self.assert_successful_execution()
        self.assert_in_output("Uploading file: test1.png")
        self.assert_in_output("Uploading file: test2.png")
        self.assert_in_output("Chapter uploaded successfully.")

    def test_set_publish_date_for_chapter(self):
        # Test invalid course label.
        self.run_admin_cmd(
            "set-publish-date fakecourse fakebook --chapter-number 10 --publish-date \"2021-06-10T10:15\""
        )
        self.assert_unsuccessful_execution()
        self.assert_in_output("The requested course label does not exist.")

        # Test invalid book.
        self.run_admin_cmd(
            "set-publish-date TestCourse0 fakebook --chapter-number 10 --publish-date \"2021-06-10T10:15\""
        )
        self.assert_unsuccessful_execution()
        self.assert_in_output("Input book not found.")

        # Test invalid chapter number.
        self.run_admin_cmd(
            "set-publish-date TestCourse0 TestBook1 --chapter-number 10 --publish-date \"2021-06-10T10:15\""
        )
        self.assert_unsuccessful_execution()
        self.assert_in_output("Input chapter not found.")

        # Test invalid chapter label.
        self.run_admin_cmd(
            "set-publish-date TestCourse0 TestBook1 --chapter-label fakelabel --publish-date \"2021-06-10T10:15\""
        )
        self.assert_unsuccessful_execution()
        self.assert_in_output("Input chapter not found.")

        # Test success in setting date for chapter.
        self.run_admin_cmd(
            "set-publish-date TestCourse0 TestBook1 --chapter-label TestChapter1 --publish-date \"2021-06-10T10:15\""
        )
        self.assert_in_output("Successfully set publish date for the chapter.")

        self.run_admin_cmd(
            "set-publish-date TestCourse0 TestBook1 --chapter-number 1 --publish-on-week \"3/5, 14:30\""
        )
        self.assert_in_output("Successfully set publish date for the chapter.")


server_process = None
def setUpModule():
    # Start the server in a subprocess.
    logging.basicConfig(stream=sys.stderr)
    logger = logging.getLogger("TESTLOG")
    logger.setLevel(logging.DEBUG)

    global server_process
    server_process = subprocess.Popen(["python3", "test_server.py"])

    time.sleep(1)

def tearDownModule():
    server_process.kill()

if __name__ == '__main__':
    unittest.main()
