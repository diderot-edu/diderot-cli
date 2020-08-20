import argparse
import json
import os
import shlex
import sys
from pathlib import Path

from api_calls import APIError, DiderotAPIInterface
from models import Book, Chapter, Course, Lab, Part
from cli_utils import expand_file_path, print_list

assert sys.version_info >= (3, 6), "Python3.6 is required"


# Custom formatter for argparse which displays all positional arguments first.
class Formatter(argparse.HelpFormatter):
    # Use defined argument order to display usage.
    def _format_usage(self, usage, actions, groups, prefix):
        if prefix is None:
            prefix = "usage: "

        # If usage is specified, use that.
        if usage is not None:
            usage = usage % dict(prog=self._prog)

        # If no optionals or positionals are available, usage is just prog.
        elif usage is None and not actions:
            usage = "%(prog)s" % dict(prog=self._prog)
        elif usage is None:
            prog = "%(prog)s" % dict(prog=self._prog)
            # Build full usage string.
            action_usage = self._format_actions_usage(actions, groups)  # NEW
            usage = " ".join([s for s in [prog, action_usage] if s])
            # Omit the long line wrapping code.
        # Prefix with 'usage:'.
        return "%s%s\n\n" % (prefix, usage)


# exit_with_error prints an error message and exist with ret code 1.
def exit_with_error(error_msg):
    print(error_msg)
    sys.exit(1)


DEFAULT_CRED_LOCATIONS = ["~/private/.diderot/credentials", "~/.diderot/credentials"]


# Command line argument generator for the CLI.
# Returns a parser that can be extended with additional commands.
class DiderotCLIArgs(object):
    # Generate a base parser object for use by both the user and admin CLI's.
    @staticmethod
    def generate_parser(prog, desc):
        parser = argparse.ArgumentParser(prog=prog, description=desc, formatter_class=Formatter)
        # Basic arguments not tied to a particular CLI version.
        parser.add_argument("--url", default="https://api.diderot.one")
        parser.add_argument("--username", default=None)
        parser.add_argument("--password", default=None)
        parser.add_argument(
            "--credentials",
            default=None,
            help="Read credentials from a credentials file. \
                                  The credential file format is a text file with the \
                                  username on the first line and the password on the second.",
        )
        return parser

    # Generate a parser for the user CLI.
    @staticmethod
    def generate_user_parser(prog, desc):
        parser = DiderotCLIArgs.generate_parser(prog, desc)
        subparsers = parser.add_subparsers(title="command", help="Different commands.", dest="command")
        subparsers.required = True

        # Subparser for list_assignments.
        list_assignments = subparsers.add_parser(
            "list_assignments", help="List all assignments in a course.", formatter_class=Formatter
        )
        list_assignments.add_argument("course", help="Course to list assignments of.")

        # Subparser for list_courses.
        list_courses = subparsers.add_parser("list_courses", help="List all courses.", formatter_class=Formatter)

        # Subparser for submit_assignment.
        submit_assignment = subparsers.add_parser(
            "submit_assignment", help="Submit handin to assignment.", formatter_class=Formatter
        )
        submit_assignment.add_argument("course", help="Course to submit assignment to.")
        submit_assignment.add_argument("homework", help="Homework to submit to.")
        submit_assignment.add_argument("handin_path", help="Path to handin file.")

        # Subparser for download_assignment.
        download_assignment = subparsers.add_parser(
            "download_assignment", help="Download homework handout files.", formatter_class=Formatter
        )
        download_assignment.add_argument("course", help="Course to download assignment from.")
        download_assignment.add_argument("homework", help="Homework assignment to download.")

        return parser, subparsers

    # Generate a parser for the admin CLI.
    @staticmethod
    def generate_admin_parser(prog, desc):
        parser, subparsers = DiderotCLIArgs.generate_user_parser(prog, desc)

        # Subparser for create_chapter.
        create_chapter = subparsers.add_parser(
            "create_chapter", help="Create a chapter in a book.", formatter_class=Formatter
        )
        create_chapter.add_argument("course", help="Course that the book belongs to.")
        create_chapter.add_argument("book", help="Book to create a chapter within.")
        create_chapter.add_argument(
            "--part",
            help="Part number that the chapter belong within. \
                            This is not needed if the book is a booklet.",
        )
        create_chapter.add_argument("--number", help="Number of the new chapter.", required=True)
        create_chapter.add_argument("--title", help="Optional title of new chapter (default = Chapter)", default=None)
        create_chapter.add_argument(
            "--label", help="Optional label of new chapter (default= randomly generated)", default=None
        )

        # Subparser for create_part.
        create_part = subparsers.add_parser("create_part", help="Create a part in a book", formatter_class=Formatter)
        create_part.add_argument("course", help="Course that the book belongs to.")
        create_part.add_argument("book", help="Book to create part in.")
        create_part.add_argument("title", help="Title of the new part.")
        create_part.add_argument("number", help="Number of the new part.")
        create_part.add_argument("--label", help="Label for the new part (default = random).", default=None)

        # Subparsers for release/unrelease chapter.
        release_chapter = subparsers.add_parser(
            "release_chapter", help="Release a book chapter", formatter_class=Formatter
        )
        release_chapter.add_argument("course", help="Course to release chapter in.")
        release_chapter.add_argument("book", help="Book that the chapter belongs to.")
        chapter_id_group = release_chapter.add_mutually_exclusive_group(required=True)
        chapter_id_group.add_argument("--chapter_number", default=None, help="Number of chapter to release.")
        chapter_id_group.add_argument("--chapter_label", default=None, help="Label of chapter to release.")

        unrelease_chapter = subparsers.add_parser(
            "unrelease_chapter", help="Unrelease a book chapter", formatter_class=Formatter
        )
        unrelease_chapter.add_argument("course", help="Course to unrelease chapter in.")
        unrelease_chapter.add_argument("book", help="Book that the chapter belongs to.")
        chapter_id_group = unrelease_chapter.add_mutually_exclusive_group(required=True)
        chapter_id_group.add_argument("--chapter_number", default=None, help="Number of chapter to unrelease.")
        chapter_id_group.add_argument("--chapter_label", default=None, help="Label of chapter to unrelease.")

        # Subparser for list_books.
        list_books = subparsers.add_parser("list_books", help="List all books.", formatter_class=Formatter)
        list_books.add_argument("course", help="Course label to filter book results by.", default=None, nargs="?")
        list_books.add_argument("--all", action="store_true", help="Optional flag to show all books visible to user.")

        # Subparser for list_chapters.
        list_chapters = subparsers.add_parser(
            "list_chapters", help="List all chapters in a book.", formatter_class=Formatter
        )
        list_chapters.add_argument("course", help="Course that the book belongs to.")
        list_chapters.add_argument("book", help="Book to list chapters of.")
        # TODO (rohany): add a filter by parts here.

        # Subparser for list_parts.
        list_parts = subparsers.add_parser("list_parts", help="List all parts of a book.", formatter_class=Formatter)
        list_parts.add_argument("course", help="Course that the book belongs to.")
        list_parts.add_argument("book", help="Book to list parts of.")

        # Subparser for update_assignment.
        update_assignment = subparsers.add_parser(
            "update_assignment", help="Update the files linked to an assignment.", formatter_class=Formatter
        )
        update_assignment.add_argument("course", type=str, help="Course that assignment belongs to.")
        update_assignment.add_argument("homework", type=str, help="Name of assignment to update.")
        update_assignment.add_argument("--autograde-tar", type=str, help="Autograder tar for the assignment.")
        update_assignment.add_argument("--autograde-makefile", type=str, help="Autograder Makefile for the assignment.")
        update_assignment.add_argument("--writeup", type=str, help="PDF writeup for the assignment.")
        update_assignment.add_argument("--handout", type=str, help="Student handout for the assignment.")

        # Subparser for upload_chapter.
        upload_chapter = subparsers.add_parser(
            "upload_chapter", help="Upload content to a chapter.", formatter_class=Formatter
        )
        upload_chapter.add_argument("course", help="Course to upload chapter to.")
        upload_chapter.add_argument("book", help="Book that the chapter belongs to.")
        chapter_id_group = upload_chapter.add_mutually_exclusive_group(required=True)
        chapter_id_group.add_argument("--chapter_number", default=None, help="Number of chapter to upload to.")
        chapter_id_group.add_argument("--chapter_label", default=None, help="Label of chapter to upload to.")
        file_type_group = upload_chapter.add_mutually_exclusive_group(required=True)
        file_type_group.add_argument("--pdf", default=None, help="Upload PDF content.")
        file_type_group.add_argument("--slides", default=None, help="Upload a slideshow in PDF format.")
        file_type_group.add_argument("--xml", default=None, help="Upload an XML/MLX document.")
        upload_chapter.add_argument("--video_url", default=None, help="URL to a video to embed into the chapter.")
        upload_chapter.add_argument("--xml_pdf", default=None, help="PDF version of the XML document for printing.")
        upload_chapter.add_argument(
            "--attach",
            type=str,
            nargs="+",
            default=None,
            help="A list of files, folders, or globs to upload as attachments for an XML/MLX document. \
                                          Folders are recursively traversed.",
        )

        # Subparser for bulk book uploads.
        upload_book = subparsers.add_parser(
            "upload_book", help="Perform bulk upload of book content.", formatter_class=Formatter
        )
        upload_book.add_argument("course", help="Course that the book belongs to.")
        upload_book.add_argument("upload_data", help="JSON upload details file.")

        return parser, subparsers

    # Verify argument information about both the admin and user CLI's.
    @staticmethod
    def validate_args(args):
        if (args.password is None and args.username is not None) or (
            args.password is not None and args.username is None
        ):
            exit_with_error("Please supply both username and password")
        if args.credentials is not None and (args.username is not None or args.password is not None):
            exit_with_error("Cannot use a credentials file and input a username/password")


# Class implementing the DiderotUser CLI.
class DiderotUser(object):
    def __init__(self, line=None):
        parser, _ = DiderotCLIArgs.generate_user_parser("diderot", "User CLI interface for Diderot.")
        if line is None:
            self.args = parser.parse_args()
        else:
            self.args = parser.parse_args(shlex.split(line))
        DiderotCLIArgs.validate_args(self.args)

    def setup_client(self):
        self.username = self.args.username
        self.password = self.args.password
        if self.username is None:
            creds = DEFAULT_CRED_LOCATIONS
            if self.args.credentials is not None:
                creds = [self.args.credentials] + creds
            for c in creds:
                p = Path(c).expanduser()
                if p.is_file():
                    if (p.stat().st_mode & 0o177) != 0:
                        exit_with_error(
                            "Credentials file must have 0600 permissions. Run `chmod 600 <credentials>` first."
                        )
                    f = p.open("r")
                    data = f.read().strip().split("\n")
                    self.username = data[0]
                    self.password = data[1]
                    f.close()
                    break
                else:
                    if c == self.args.credentials:
                        exit_with_error("Input credentials path is invalid.")
        if self.username is None:
            exit_with_error("Supply your credentials via the CLI or a credentials file!")
        self.api_client = DiderotAPIInterface(self.args.url)
        self.api_client.connect(self.username, self.password)

    def dispatch(self):
        commands = {
            "download_assignment": self.download_assignment,
            "list_assignments": self.list_assignments,
            "list_courses": self.list_courses,
            "submit_assignment": self.submit_assignment,
        }
        func = commands.get(self.args.command, None)
        if func is None:
            exit_with_error("Error parsing.")
        try:
            self.setup_client()
            func()
        except APIError as e:
            exit_with_error(str(e))
        self.api_client.client.close()

    # For maintainability, keep the dispatch functions in alphabetical order.

    def download_assignment(self):
        self.api_client.download_assignment(self.args.course, self.args.homework)
        print("Successfully downloaded assignment.")

    def list_assignments(self):
        course = Course(self.api_client.client, self.args.course)
        labs = [hw["name"] for hw in Lab.list(course)]
        if len(labs) == 0:
            print("Course has no labs.")
        else:
            print_list(labs)

    def list_courses(self):
        print_list([c["label"] for c in Course.list(self.api_client.client)])

    def submit_assignment(self):
        try:
            self.api_client.submit_assignment(self.args.course, self.args.homework, self.args.handin_path)
            print("Assignment submitted successfully. Track your submission's status on Diderot.")
        except APIError as e:
            print(str(e))
            exit_with_error("Something went wrong. Please try submitting on the Diderot website.")


# Class implementing DiderotAdmin CLI.
class DiderotAdmin(DiderotUser):
    def __init__(self, line=None, sleep_time=5):
        parser, _ = DiderotCLIArgs.generate_admin_parser("diderot_admin", "Admin CLI interface for Diderot.")
        if line is None:
            self.args = parser.parse_args()
        else:
            self.args = parser.parse_args(shlex.split(line))
        self.sleep_time = sleep_time
        DiderotCLIArgs.validate_args(self.args)

    def dispatch(self):
        commands = {
            "create_chapter": self.create_chapter,
            "create_part": self.create_part,
            "list_books": self.list_books,
            "list_chapters": self.list_chapters,
            "list_parts": self.list_parts,
            "release_chapter": self.release_chapter,
            "unrelease_chapter": self.unrelease_chapter,
            "update_assignment": self.update_assignment,
            "upload_book": self.upload_book,
            "upload_chapter": self.upload_chapter,
        }
        func = commands.get(self.args.command, None)
        try:
            if func is None:
                super().dispatch()
            else:
                self.setup_client()
                func()
        except APIError as e:
            exit_with_error(str(e))

    # For maintainability, keep the dispatch functions in alphabetical order.

    def create_chapter(self):
        self.api_client.create_chapter(
            self.args.course, self.args.book, self.args.part, self.args.number, self.args.title, self.args.label
        )
        print("Successfully created chapter.")

    def create_part(self):
        self.api_client.create_part(
            self.args.course, self.args.book, self.args.number, self.args.title, self.args.label
        )
        print("Successfully created part.")

    def list_books(self):
        res = self.api_client.list_books(self.args.course, all=self.args.all)
        print_list([c["label"] for c in res])

    def list_chapters(self):
        course = Course(self.api_client.client, self.args.course)
        book = Book(course, self.args.book)
        print_list(
            [
                "{}. {}".format(str(float(c["rank"])).rstrip("0").rstrip("."), c["title"])
                for c in Chapter.list(course, book)
            ]
        )

    def list_parts(self):
        course = Course(self.api_client.client, self.args.course)
        book = Book(course, self.args.book)
        print_list(["{}. {}".format(c["rank"], c["title"]) for c in Part.list(course, book)])

    def release_chapter(self):
        self.api_client.release_unrelease_chapter(self.args.course, self.args.book, self.args, release=True)
        print("Success releasing chapter.")

    def unrelease_chapter(self):
        self.api_client.release_unrelease_chapter(self.args.course, self.args.book, self.args, release=False)
        print("Success unreleasing chapter.")

    def update_assignment(self):
        try:
            self.api_client.update_assignment(self.args.course, self.args.homework, self.args)
            print("Success uploading files.")
        except APIError as e:
            print(str(e))
            exit_with_error("Uploading files failed. Try using the Web UI.")

    def upload_book(self):
        file_path = expand_file_path(self.args.upload_data)
        if not os.path.exists(file_path):
            exit_with_error("input file path {} does not exist".format(file_path))
        with open(file_path, "rb") as schema:
            try:
                book_data = json.load(schema)
            except Exception as e:
                exit_with_error("Failed loading json schema with error: {}".format(e))

        def get_or_none(obj, field):
            if field in obj:
                return obj[field]
            return None

        file_prefix = os.path.dirname(file_path)

        def adjust_search_path(path):
            if path is None:
                return None
            return os.path.join(file_prefix, path)

        # Collect the necessary Diderot objects.
        course = Course(self.api_client.client, self.args.course)
        book_label = get_or_none(book_data, "book")
        # Try out "label", more consistent with Diderot terminology
        if book_label is None:
            book_label = get_or_none(book_data, "label")
        # If book label is still None, then error out.
        if book_label is None:
            exit_with_error("Please specify a valid book to upload into")
        book = Book(course, book_label)

        # If the upload contains parts, create them.
        parts = get_or_none(book_data, "parts")
        if parts is not None:
            for part in parts:
                if not Part.exists(course, book, get_or_none(part, "number")):
                    self.api_client.create_part(
                        course.label,
                        book.label,
                        get_or_none(part, "number"),
                        get_or_none(part, "title"),
                        get_or_none(part, "label"),
                    )

        # Upload and maybe create the chapters in the input.
        chapters = get_or_none(book_data, "chapters")
        if chapters is None:
            exit_with_error("invalid JSON: could not find field 'chapters'")
        for chapter in chapters:
            # Extract data from chapter json
            number = get_or_none(chapter, "number")
            label = get_or_none(chapter, "label")
            title = get_or_none(chapter, "title")
            attachments = get_or_none(chapter, "attachments")

            self.args.pdf = adjust_search_path(get_or_none(chapter, "pdf"))
            self.args.slides = adjust_search_path(get_or_none(chapter, "slides"))
            self.args.video_url = adjust_search_path(get_or_none(chapter, "video"))
            self.args.xml = adjust_search_path(get_or_none(chapter, "xml"))
            self.args.xml_pdf = adjust_search_path(get_or_none(chapter, "xml_pdf"))

            if number is None:
                exit_with_error(f"invalid JSON: must provide field 'number' for chapter {chapter}")

            # If the target chapter does not exist, then create it.
            if not Chapter.exists(course, book, number):
                part_num = get_or_none(chapter, "part")
                # Non-booklets need parts for their chapters.
                if not book.is_booklet and part_num is None:
                    exit_with_error("Chapter creation in a book requires 'part' field for chapters")
                self.api_client.create_chapter(course.label, book.label, part_num, number, title, label)
                print(f"Successfully created chapter number ({number}), label ({label}, title ({title}).")

            # Upload the target files to the chapter now.
            self.args.attach = None
            if attachments is not None:
                self.args.attach = [adjust_search_path(path) for path in attachments]
            # Set default arguments that we wont use, but upload_chapter expects.
            print(f"Uploading chapter number: {number}...")
            try:
                self.api_client.upload_chapter(
                    course.label, book.label, number, None, self.args, sleep_time=self.sleep_time,
                )
            except APIError as e:
                exit_with_error("Failure uploading chapter. Aborting")
            print("Successfully uploaded chapter.")

    def upload_chapter(self):
        if self.args.video_url is not None and self.args.xml is not None:
            exit_with_error("Cannot use --video_url with xml uploads.\nFailure uploading chapter.")
        if self.args.attach is not None and self.args.xml is None:
            exit_with_error("Cannot use --attach if not uploading xml/mlx.\nFailure uploading chapter.")
        self.api_client.upload_chapter(
            self.args.course,
            self.args.book,
            self.args.chapter_number,
            self.args.chapter_label,
            self.args,
            sleep_time=self.sleep_time,
        )
        print("Chapter uploaded successfully.")
