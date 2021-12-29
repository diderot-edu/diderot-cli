import click
import json
import os

import diderot_cli.arguments as args
import diderot_cli.options as opts

from diderot_cli.commands import diderot_user
from diderot_cli.context import DiderotContext, pass_diderot_context
from diderot_cli.diderot_api import uses_api
from diderot_cli.models import Book, Chapter, Course, Part
from diderot_cli.utils import (
    BookNotFoundAPIError,
    debug as debug_echo,
    exit_with_error,
    expand_file_path,
    print_list,
)


@click.group()
@opts.api
@opts.debug
@pass_diderot_context
def admin(dc: DiderotContext, **opts):
    "Admin related actions."

    dc.url = opts.get("url")
    dc.credentials = opts.get("credentials")
    dc.username = opts.get("username")
    dc.password = opts.get("password")
    dc.debug = opts.get("debug")

    debug_echo(f"Context object: {dc}")


@click.command("create_book")
@args.multi_args(args.course, args.title, args.book_label)
@uses_api
@pass_diderot_context
def create_book(dc: DiderotContext, course: str, title: str, book_label: str):
    dc.client.create_book(course, title, book_label)
    click.echo("Successfully created book.")


@click.command("create_chapter")
@args.multi_args(args.course, args.book)
@opts.multi_opts(opts.part_number, opts.chapter_number, opts.chapter_label, opts.title)
@uses_api
@pass_diderot_context
def create_chapter(dc: DiderotContext, course: str, book: str, **options):
    dc.client.create_chapter(course, book, **options)
    click.echo("Successfully created chapter.")


@click.command("create_part")
@args.multi_args(args.course, args.book, args.title)
@opts.multi_opts(opts.part_number, opts.part_label)
@uses_api
@pass_diderot_context
def create_part(dc: DiderotContext, course: str, book: str, title: str, **options):
    dc.client.create_part(course, book, title, **options)
    click.echo("Successfully created part.")


@click.command("list_books")
@args.optional_course
@click.option("--all", type=click.BOOL, default=False, is_flag=True)
@uses_api
@pass_diderot_context
def list_books(dc: DiderotContext, course: str, all: bool):
    res = dc.client.list_books(course, all=all)
    print_list([c["label"] for c in res])


@click.command("list_chapters")
@args.multi_args(args.course, args.book)
@uses_api
@pass_diderot_context
def list_chapters(dc: DiderotContext, course: str, book: str):
    course = Course(dc.client.client, course)
    book = Book(course, book)
    print_list(
        [
            "{}. {}".format(str(float(c["rank"])).rstrip("0").rstrip("."), c["title"])
            for c in Chapter.list(course, book)
        ]
    )


@click.command("list_parts")
@args.multi_args(args.course, args.book)
@uses_api
@pass_diderot_context
def list_parts(dc: DiderotContext, course: str, book: str):
    course = Course(dc.client.client, course)
    book = Book(course, book)
    print_list(["{}. {}".format(c["rank"], c["title"]) for c in Part.list(course, book)])


@click.command("publish_chapter")
@args.multi_args(args.course, args.book)
@opts.multi_opts(opts.chapter_number, opts.chapter_label)
@uses_api
@pass_diderot_context
def publish_chapter(dc: DiderotContext, course: str, book: str, **options):
    dc.client.release_unrelease_chapter(course, book, release=True, **options)
    click.echo("Success publishing chapter.")


@click.command("set_publish_date")
@args.multi_args(args.course, args.book)
@opts.multi_opts(opts.chapter_number, opts.chapter_label, opts.publish_date, opts.publish_on_week)
@uses_api
@pass_diderot_context
def set_publish_date(dc: DiderotContext, course: str, book: str, **options):
    dc.client.set_publish_date(course, book, **options)
    click.echo("Successfully set publish date for the chapter.")


@click.command("retract_chapter")
@args.multi_args(args.course, args.book)
@opts.multi_opts(opts.chapter_number, opts.chapter_label)
@uses_api
@pass_diderot_context
def retract_chapter(dc: DiderotContext, course: str, book: str, **options):
    dc.client.release_unrelease_chapter(course, book, release=False, **options)
    click.echo("Success retracting chapter.")


@click.command("update_assignment")
@args.multi_args(args.course, args.homework)
@opts.multi_opts(opts.autograde_tar, opts.autograde_makefile, opts.handout)
@uses_api
@pass_diderot_context
def update_assignment(dc: DiderotContext, course: str, homework: str, **options):
    dc.client.update_assignment(course, homework, **options)
    click.echo("Success uploading files.")


@click.command("upload_book")
@args.course
@click.argument("upload-data", type=click.Path(exists=True))  # Path? re-check this
@opts.sleep_time
@uses_api
@pass_diderot_context
def upload_book(dc: DiderotContext, course: str, upload_data: str, **options):
    file_path = expand_file_path(upload_data)

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
    course = Course(dc.client.client, course)
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
    if union_chapter_numbers != set(range(1, len(union_chapter_numbers) + 1)):
        exit_with_error(f"invalid JSON: resulting chapters numbers are inconsistent, "
                        f"should be a sequence of integers starting with 1 including existing chapters. "
                        f"Current numbers set is: {actual_chapter_numbers} and resulting using json "
                        f"is {union_chapter_numbers}")

    # If the upload contains parts, create them.
    parts = get_or_none(book_data, "parts")
    if parts is not None:
        for part in parts:
            if not Part.exists(course, book, get_or_none(part, "number")):
                dc.client.create_part(
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

        book = book_label
        part_num = get_or_none(chapter, "part")
        # pdf = adjust_search_path(get_or_none(chapter, "pdf"))
        # video_url = adjust_search_path(get_or_none(chapter, "video"))
        # xml = adjust_search_path(get_or_none(chapter, "xml"))
        # xml_pdf = adjust_search_path(get_or_none(chapter, "xml_pdf"))
        publish_date = get_or_none(chapter, "publish_on_date")
        publish_on_week = get_or_none(chapter, "publish_on_week")

        if number is None:
            exit_with_error(f"invalid JSON: must provide field 'number' for chapter {chapter}")

        if Chapter.exists(course, book, number):
            dc.client.set_publish_date(course, book, **options)
        else:
            if part_num is None:
                exit_with_error("Chapter creation in a book requires 'part' field for chapters")

            dc.client.create_chapter(
                course.label, book.label, part_num, number, title, label, publish_date, publish_on_week
            )
            click.echo(f"Successfully created chapter number ({number}), label ({label}, title ({title}).")

        # Upload the target files to the chapter now.
        attach = None
        if attachments is not None:
            attach = [adjust_search_path(path) for path in attachments]
        # Set default arguments that we wont use, but upload_chapter expects.
        click.echo(f"Uploading chapter number: {number}...")
        dc.client.upload_chapter(course.label, book.label, number, None, attach=attach, **options)
        click.echo("Successfully uploaded chapter.")


@click.command("upload_chapter")
@args.multi_args(args.course, args.book)
@opts.multi_opts(
    opts.chapter_number, opts.chapter_label,
    opts.attach, opts.pdf, opts.xml, opts.xml_pdf,
    opts.video_url, opts.attach, opts.sleep_time,
)
@uses_api
@pass_diderot_context
def upload_chapter(dc: DiderotContext, course: str, book: str, chapter_number: int, chapter_label: str, **options):
    attached_files = options.get("attach", [])
    if len(attached_files) > 0 and options.get("xml") is None:
        exit_with_error("Cannot use --attach if not uploading xml/mlx.\nFailure uploading chapter.")

    dc.client.upload_chapter(
        course,
        book,
        chapter_number,
        chapter_label,
        **options,
    )
    click.echo("Chapter uploaded successfully.")


def register_commands(click_group: click.Group):
    commands = [
        create_book,
        create_chapter,
        create_part,
        list_books,
        list_chapters,
        list_parts,
        publish_chapter,
        set_publish_date,
        retract_chapter,
        update_assignment,
        upload_book,
        upload_chapter,
        diderot_user.download_assignment,
        diderot_user.list_assignments,
        diderot_user.list_courses,
        diderot_user.submit_assignment,
    ]

    for c in commands:
        admin.add_command(c)

    click_group.add_command(admin)
