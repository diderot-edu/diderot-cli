import json
import os
import shlex

from .diderot_cli_args import DiderotCLIArgs
from .diderot_user import DiderotUser

from models import Book, Chapter, Course, Part
from utils import BookNotFoundAPIError, APIError, exit_with_error, print_list, expand_file_path

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
            "create_book": self.create_book,
            "create_chapter": self.create_chapter,
            "create_part": self.create_part,
            "list_books": self.list_books,
            "list_chapters": self.list_chapters,
            "list_parts": self.list_parts,
            "publish_chapter": self.publish_chapter,
            "set_publish_date": self.set_publish_date,
            "retract_chapter": self.retract_chapter,
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

    def create_book(self):
        self.api_client.create_book(
            self.args.course, self.args.title, self.args.label
        )
        print("Successfully created book.")

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

    def publish_chapter(self):
        self.api_client.release_unrelease_chapter(self.args.course, self.args.book, self.args, release=True)
        print("Success publishing chapter.")

    def set_publish_date(self):
        self.api_client.set_publish_date(self.args.course, self.args.book, self.args)
        print("Successfully set publish date for the chapter.")

    def retract_chapter(self):
        self.api_client.release_unrelease_chapter(self.args.course, self.args.book, self.args, release=False)
        print("Success retracting chapter.")

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

        book_title = book_data.get("title", book_label)

        try:
            book = Book(course, book_label)
        except BookNotFoundAPIError:
            Book.create(course, book_title, book_label)
            book = Book(course, book_label)

        book_data_chapters = book_data.get("chapters", [])

        book_data_parts = book_data.get("parts", [])
        book_data_part_numbers = set([c.get("number") for c in book_data_parts])
        chapters_data_part_numbers = set([c.get("part") for c in book_data_chapters])
        actual_part_numbers = set([int(float(c["rank"])) for c in Part.list(course, book)])
        union_part_numbers = actual_part_numbers.union(book_data_part_numbers)
        if union_part_numbers != set(range(1, len(union_part_numbers) + 1)):
            exit_with_error(f"invalid JSON: resulting parts numbers are inconsistent, "
                            f"should be a sequence of integers starting with 1 including existing parts. "
                            f"Current numbers set is: {actual_part_numbers} and resulting using json "
                            f"is {union_part_numbers}")
        elif not chapters_data_part_numbers.issubset(union_part_numbers):
            exit_with_error(f"invalid JSON: some parts numbers for chapters are invalid. "
                            f"Resulting part number set (existing and new) is {union_part_numbers} and specified in"
                            f" chapter number set is {chapters_data_part_numbers}")

        book_data_chapter_numbers = set([c.get("number") for c in book_data_chapters])
        actual_chapter_numbers = set([int(float(c["rank"])) for c in Chapter.list(course, book)])
        union_chapter_numbers = actual_chapter_numbers.union(book_data_chapter_numbers)
        if union_chapter_numbers != set(range(1, len(union_chapter_numbers)+1)):
            exit_with_error(f"invalid JSON: resulting chapters numbers are inconsistent, "
                            f"should be a sequence of integers starting with 1 including existing chapters. "
                            f"Current numbers set is: {actual_chapter_numbers} and resulting using json "
                            f"is {union_chapter_numbers}")

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

            self.args.book = book_label
            self.args.part_num = get_or_none(chapter, "part")
            self.args.chapter_number = number
            self.args.chapter_label = label
            self.args.pdf = adjust_search_path(get_or_none(chapter, "pdf"))
            self.args.video_url = adjust_search_path(get_or_none(chapter, "video"))
            self.args.xml = adjust_search_path(get_or_none(chapter, "xml"))
            self.args.xml_pdf = adjust_search_path(get_or_none(chapter, "xml_pdf"))
            self.args.publish_date = get_or_none(chapter, "publish_on_date")
            self.args.publish_on_week = get_or_none(chapter, "publish_on_week")


            if number is None:
                exit_with_error(f"invalid JSON: must provide field 'number' for chapter {chapter}")

            if Chapter.exists(course, book, number):
                self.set_publish_date()
            else:
                # create chapter
                if self.args.part_num is None:
                    exit_with_error("Chapter creation in a book requires 'part' field for chapters")
                self.api_client.create_chapter(
                    course.label, book.label, self.args.part_num, number, title, label, self.args.publish_date, self.args.publish_on_week)
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
                print(e)
                exit_with_error("Failure uploading chapter. Aborting")
            print("Successfully uploaded chapter.")

    def upload_chapter(self):
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
