import requests
from pathlib import Path
import shlex
import argparse
from importlib import util
import importlib
import api_calls
import os.path
import shutil
import getpass
import cmd
import sys
assert sys.version_info >= (3, 6), 'Python3.6 is required'

requests_spec = importlib.util.find_spec('requests')
if requests_spec is None:
    print('Requests library not found!')
    print('Please install it using `pip3 install --user requests`')


# custom formatter for argparse

class Formatter(argparse.HelpFormatter):
    # use defined argument order to display usage
    def _format_usage(self, usage, actions, groups, prefix):
        if prefix is None:
            prefix = 'usage: '

        # if usage is specified, use that
        if usage is not None:
            usage = usage % dict(prog=self._prog)

        # if no optionals or positionals are available, usage is just prog
        elif usage is None and not actions:
            usage = '%(prog)s' % dict(prog=self._prog)
        elif usage is None:
            prog = '%(prog)s' % dict(prog=self._prog)
            # build full usage string
            action_usage = self._format_actions_usage(actions, groups)  # NEW
            usage = ' '.join([s for s in [prog, action_usage] if s])
            # omit the long line wrapping code
        # prefix with 'usage:'
        return '%s%s\n\n' % (prefix, usage)


# Argument generator for the CLI
class DiderotCLIArgumentGenerator(object):
    @staticmethod
    def generate_args():
        parser = argparse.ArgumentParser(
            prog="diderot_admin", description="Diderot admin CLI")
        parser.add_argument("--url", default="https://www.diderot.one")
        parser.add_argument("--username", default=None)
        parser.add_argument("--password", default=None)
        parser.add_argument("--credentials", default="~/.diderot/credentials")
        parser.add_argument("--command", default=None,
                            help="Use this argument with a string to execute that specific command and return rather than entering the repl.")
        args = parser.parse_args()
        if (args.password is None and args.username is not None) or \
           (args.password is not None and args.username is None):
            print("Please supply both username and password")
            sys.exit(0)
        if args.credentials != '~/.diderot/credentials' and (args.username is not None or args.password is not None):
            print("Cannot use a credentials file and input a username/password")
            sys.exit(0)
        return args


# The basic architecture of this CLI is based on usage of the cmd.Cmd
# python package, which makes it easy to implement a REPL. The library
# lets you implement different commands for the REPL by letting users
# implement do_<cmd name> and help_<cmd name> functions. For example,
# the function do_list_assignments is called when the command
# list_assignments is entered into the REPL. It is given the lines,
# which is the rest of the input to the command. The function
# help_list_assignments is the same, and is invoked when a user enters
# help list_assignments. To add a command to the REPL, just add the
# appropriate function to DiderotCLI class. To interface with
# the diderot website, the DiderotCLI class makes calls to the
# helper class DiderotAPIInterface, which makes requests to diderot.
class DiderotCLI(cmd.Cmd):

    prompt = "DiderotCLI >> "

    def __init__(self, url, username, password, credPath, shouldPrintLoginMessage=True):
        self.url = url
        self.api_client = api_calls.DiderotAPIInterface(url)
        self.logged_in = False
        self.course = None
        self.username = username
        self.password = password

        p = Path(credPath).expanduser()
        if p.is_file() and self.username is None:
            data = p.open('r').read().strip().split('\n')
            self.username = data[0]
            self.password = data[1]

        self.shouldPrintLoginMessage = shouldPrintLoginMessage
        super().__init__()

    def cmdloop(self):
        # TODO (rohany): This ctrl + c catching is a bit hacky,
        # I wonder if there is a better/more principled way to do this.
        while True:
            try:
                return cmd.Cmd.cmdloop(self, intro=None)
            except KeyboardInterrupt:
                print("^C")

    def initialize(self):
        if self.logged_in:
            return True
        if self.username is None:
            username = str(input('Username: '))
            password = getpass.getpass()
            if username == '' or password == '':
                print('Login aborted!')
                return False
        else:
            username = self.username
            password = self.password

        if not self.api_client.login(username, password, shouldPrint=self.shouldPrintLoginMessage):
            sys.exit(0)

        self.logged_in = True

    def preloop(self):
        self.initialize()

    def print_list(self, l):
        print("\n".join(l))

    def create_course_parser(self, progName):
        parser = argparse.ArgumentParser(
            prog=progName, formatter_class=Formatter)
        if self.course is None:
            parser.add_argument('course', help="Course label")
        return parser

    # Must only be used by arguments generated from
    # parsers created with `create_course_parser`
    def fix_course_args(self, args):
        if self.course is not None:
            args.course = self.course
        return args

    def do_set_course(self, line):
        args = self.parse_set_course(line)
        if args is None:
            return
        if not self.api_client.verify_course_label(args.course):
            return
        self.course = args.course
        self.prompt = "DiderotCLI/{} >> ".format(args.course)
        print("Course set successfully.")

    def parse_set_course(self, args):
        parser = argparse.ArgumentParser(prog="set_course")
        parser.add_argument('course', help="Course label")
        try:
            return parser.parse_args(shlex.split(args))
        except SystemExit:
            return None

    def help_set_course(self, line):
        self.parse_set_course("set_course -h")

    def do_unset_course(self, line):
        args = self.parse_unset_course(line)
        if args is None:
            return
        self.course = None
        self.prompt = "DiderotCLI >> "
        print("Course unset successfully.")

    def parse_unset_course(self, args):
        parser = argparse.ArgumentParser(prog="unset_course")
        try:
            return parser.parse_args(shlex.split(args))
        except SystemExit:
            return None

    def help_unset_course(self, line):
        self.parse_unset_course("unset_course -h")

    def do_list_courses(self, line):
        if self.parse_list_courses(line) is None:
            return
        result = self.api_client.list_all_courses()
        if result is None:
            print("Error retrieving all courses.")
        else:
            self.print_list([c['label'] for c in result])

    def parse_list_courses(self, args):
        parser = argparse.ArgumentParser(prog="list_courses")
        try:
            return parser.parse_args(shlex.split(args))
        except SystemExit:
            return None

    def help_list_courses(self):
        self.parse_list_courses("list_courses -h")

    def do_list_assignments(self, args):
        args = self.parse_list_assignments(args)
        if args is None:
            return
        result = self.api_client.list_assignments(args.course)
        if result is None:
            print("Error retrieving all assignments.")
        else:
            self.print_list([hw['name'] for hw in result])

    def parse_list_assignments(self, args):
        parser = self.create_course_parser("list_assignments")
        try:
            return self.fix_course_args(parser.parse_args(shlex.split(args)))
        except SystemExit:
            return None

    def help_list_assignments(self):
        self.parse_list_assignments("list_assignments -h")

    def do_download_assignment(self, args):
        args = self.parse_download_assignment(args)
        if args is None:
            return
        result = self.api_client.download_assignment(
            args.course, args.homework)
        if result is None:
            print("Failed to download assignment")
        else:
            print("Successfully downloaded assignment")

    def parse_download_assignment(self, args):
        parser = self.create_course_parser("download_assignment")
        parser.add_argument('homework', help='Homework name')
        try:
            return self.fix_course_args(parser.parse_args(shlex.split(args)))
        except SystemExit:
            return None

    def help_download_assignment(self):
        self.parse_download_assignment("download_assignment -h")

    def do_submit_assignment(self, args):
        args = self.parse_submit_assignment(args)
        if args is None:
            return
        success, res_url = self.api_client.submit_assignment(
            args.course, args.homework, args.handin_path)
        if success:
            print("Assignment submitted successfully. Track your submission's status at the following url: {}".format(res_url))
        else:
            print("Something went wrong. Please try submitting on the Diderot website.")

    def parse_submit_assignment(self, args):
        parser = self.create_course_parser("submit_assignment")
        parser.add_argument('homework', help='Assignment name')
        parser.add_argument('handin_path', help='Path to handin')
        try:
            return self.fix_course_args(parser.parse_args(shlex.split(args)))
        except SystemExit:
            return None

    def help_submit_assignment(self):
        self.parse_submit_assignment("submit_assignment -h")

    def emptyline(self):
        pass

    # Functions to handle when users try and quit from the CLI.
    def do_quit(self, line):
        sys.exit(0)

    def help_quit(self):
        pass

    def do_exit(self, line):
        sys.exit(0)

    def help_exit(self):
        pass

    def do_EOF(self, line):
        return True

    def help_EOF(self):
        pass
