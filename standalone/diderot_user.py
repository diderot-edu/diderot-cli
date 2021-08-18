import shlex

from getpass import getpass
from pathlib import Path

from .diderot_api import DiderotAPIInterface
from .diderot_cli_args import DiderotCLIArgs

from constants import DEFAULT_CRED_LOCATIONS
from models import Course, Lab
from utils import APIError, exit_with_error, print_list

class DiderotUser:
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

                if not p.is_file() and c == self.args.credentials:
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
                    self.username = data[0]
                    self.password = data[1]
                break

        if self.username is None:
            try:
                self.username = input("Username: ")
            except EOFError:
                self.username = ""
            if self.username == "":
                exit_with_error("Username is required.")
        if self.password is None:
            try:
                self.password = getpass()
            except EOFError:
                self.password = ""
            if self.password == "":
                exit_with_error("Password is required.")
        self.api_client = DiderotAPIInterface(self.args.url)
        self.api_client.login(self.username, self.password)

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
