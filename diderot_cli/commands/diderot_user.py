import click

import diderot_cli.arguments as args
import diderot_cli.options as opts

from diderot_cli.constants import DEFAULT_DIDEROT_URL
from diderot_cli.context import DiderotContext, pass_diderot_context
from diderot_cli.diderot_api import uses_api
from diderot_cli.models import Course, Lab
from diderot_cli.utils import print_list, debug as debug_echo

@click.group()
@opts.api
@opts.debug
@pass_diderot_context
def student(dc: DiderotContext, **opts):
    "Student/Regular user related actions."

    dc.url = opts.get("url")
    dc.credentials = opts.get("credentials")
    dc.username = opts.get("username")
    dc.password = opts.get("password")
    dc.debug = opts.get("debug")

    debug_echo(f"Context object: {dc}")


@click.command()
@args.multi_args(args.course, args.homework)
@uses_api
@pass_diderot_context
def download_assignment(dc: DiderotContext, course, homework):
    if dc.client.download_assignment(course, homework):
        click.echo("Successfully downloaded assignment.")

@click.command()
@args.course
@uses_api
@pass_diderot_context
def list_assignments(dc: DiderotContext, course):
    course = Course(dc.client.client, course)
    labs = [hw["name"] for hw in Lab.list(course)]
    if len(labs) == 0:
        click.echo("Course has no labs.")
    else:
        print_list(labs)

@click.command()
@uses_api
@pass_diderot_context
def list_courses(dc: DiderotContext):
    print_list([c["label"] for c in Course.list(dc.client.client)])

@click.command()
@args.multi_args(args.course, args.homework, args.handin)
@uses_api
@pass_diderot_context
def submit_assignment(dc: DiderotContext, course: str, homework: str, handin: str):
    dc.client.submit_assignment(course, homework, handin)
    click.echo("Assignment submitted successfully. Track your submission's status on Diderot.")


def register_commands(click_group: click.Group):
    commands = [
        download_assignment,
        list_assignments,
        list_courses,
        submit_assignment,
    ]

    for c in commands:
        student.add_command(c)

    click_group.add_command(student)
