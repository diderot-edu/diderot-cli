import argparse

from formatter import Formatter
from utils import exit_with_error

class DiderotCLIArgs:
    """
    Command line argument generator for the CLI.
    Returns a parser that can be extended with additional commands.
    """

    @staticmethod
    def generate_parser(prog, desc):
        """Generate a base parser object for use by both the user and admin CLI's."""

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

    @staticmethod
    def generate_user_parser(prog, desc):
        """Generate a parser for the user CLI."""

        parser = DiderotCLIArgs.generate_parser(prog, desc)
        subparsers = parser.add_subparsers(title="command", help="Different commands.", dest="command")
        subparsers.required = True

        # Subparser for list_assignments.
        list_assignments = subparsers.add_parser(
            "list_assignments", help="List all assignments in a course.", formatter_class=Formatter
        )
        list_assignments.add_argument("course", help="Course to list assignments of.")

        # Subparser for list_courses.
        subparsers.add_parser("list_courses", help="List all courses.", formatter_class=Formatter)

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

    @staticmethod
    def generate_admin_parser(prog, desc):
        """Generate a parser for the admin CLI."""

        parser, subparsers = DiderotCLIArgs.generate_user_parser(prog, desc)

        # Subparser for create_book.
        # Example create_book <course label> --title <book title> --label <book label>
        create_book = subparsers.add_parser(
            "create_book", help="Create a chapter in a book.", formatter_class=Formatter
        )
        create_book.add_argument("course", help="Course that the book belongs to.")

        create_book.add_argument("--title", help="Optional title of new book (default = label)", default=None)
        create_book.add_argument(
            "--label", help="Label of new book"
        )

        # Subparser for create_chapter.
        create_chapter = subparsers.add_parser(
            "create_chapter", help="Create a chapter in a book.", formatter_class=Formatter
        )
        create_chapter.add_argument("course", help="Course that the book belongs to.")
        create_chapter.add_argument("book", help="Book to create a chapter within.")
        create_chapter.add_argument(
            "--part",
            help="Part number that the chapter belong within."
        )
        create_chapter.add_argument("--number", help="Number of the new chapter.", required=True)
        create_chapter.add_argument("--title", help="Optional title of new chapter (default = Chapter)", default=None)
        create_chapter.add_argument(
            "--label", help="Optional label of new chapter (default= randomly generated)", default=None
        )
        create_chapter.add_argument(
            "--publish_date",
            help="Optional publish date for chapter in ISO format (yyyy-mm-dd hh:mm:ss+hh:mm)", default=None
        )
        create_chapter.add_argument(
            "--due_date", help="Optional due date for chapter in ISO format (yyyy-mm-dd hh:mm:ss+hh:mm)", default=None
        )

        # Subparser for set_publish_date.
        set_publish_date = subparsers.add_parser(
            "set_publish_date", help="Set chapter publish date.", formatter_class=Formatter
        )

        set_publish_date.add_argument("course", help="Course to release chapter in.")
        set_publish_date.add_argument("book", help="Book that the chapter belongs to.")
        set_publish_date_chapter_id_group = set_publish_date.add_mutually_exclusive_group(required=True)
        set_publish_date_chapter_id_group.add_argument(
            "--chapter_number", default=None, help="Number of chapter to upload to.")
        set_publish_date_chapter_id_group.add_argument(
            "--chapter_label", default=None, help="Label of chapter to upload to.")
        set_publish_date_group = set_publish_date.add_mutually_exclusive_group(required=True)
        set_publish_date_group.add_argument(
            "--publish_date", default=None, help="Publish date for chapter in ISO format (yyyy-mm-dd hh:mm:ss+hh:mm).")
        set_publish_date_group.add_argument(
            "--publish_on_week", default=None,
            help="Publish on week from course start in format (week_num/week_day, hour:minute)")


        # Subparser for create_part.
        create_part = subparsers.add_parser("create_part", help="Create a part in a book", formatter_class=Formatter)
        create_part.add_argument("course", help="Course that the book belongs to.")
        create_part.add_argument("book", help="Book to create part in.")
        create_part.add_argument("title", help="Title of the new part.")
        create_part.add_argument("number", help="Number of the new part.")
        create_part.add_argument("--label", help="Label for the new part (default = random).", default=None)

        # Subparsers for release/unrelease chapter.
        publish_chapter = subparsers.add_parser(
            "publish_chapter", help="Release a book chapter", formatter_class=Formatter
        )
        publish_chapter.add_argument("course", help="Course to release chapter in.")
        publish_chapter.add_argument("book", help="Book that the chapter belongs to.")
        chapter_id_group = publish_chapter.add_mutually_exclusive_group(required=True)
        chapter_id_group.add_argument("--chapter_number", default=None, help="Number of chapter to release.")
        chapter_id_group.add_argument("--chapter_label", default=None, help="Label of chapter to release.")

        retract_chapter = subparsers.add_parser(
            "retract_chapter", help="Unrelease a book chapter", formatter_class=Formatter
        )
        retract_chapter.add_argument("course", help="Course to unrelease chapter in.")
        retract_chapter.add_argument("book", help="Book that the chapter belongs to.")
        chapter_id_group = retract_chapter.add_mutually_exclusive_group(required=True)
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

    @staticmethod
    def validate_args(args):
        """Verify argument information about both the admin and user CLI's."""

        password = args.password
        if args.credentials is not None and (args.username is not None or password is not None):
            exit_with_error("Cannot use a credentials file and input a username/password")
        if password is not None and args.username is None:
            exit_with_error("Please supply username")

            exit_with_error("Something went wrong. Please try submitting on the Diderot website.")
