import cmd
import sys
assert sys.version_info >= (3,6), 'Python3.6 is required'
import getpass
import shutil
import os.path
import api_calls
import importlib
from importlib import util

requests_spec = importlib.util.find_spec('requests')
if requests_spec is None:
    print('Requests library not found!')
    print('Please install it using `pip3 install --user requests`')

import requests

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

    def cmdloop(self, url):
        self.url = url
        self.api_client = api_calls.DiderotAPIInterface(url)
        self.logged_in = False

        # TODO (rohany): This ctrl + c catching is a bit hacky,
        # I wonder if there is a better/more principled way to do this.
        while True:
            try:
                return cmd.Cmd.cmdloop(self, intro=None)
            except KeyboardInterrupt:
                print("^C")
    
    def preloop(self):
        if self.logged_in:
            return True
        
        username = str(input('Username: '))
        password = getpass.getpass()

        if username == '' or password == '':
            print('Login aborted!')
            return False

        if not self.api_client.login(username, password):
            sys.exit(0)

        self.logged_in = True
    
    def do_list_courses(self, line):
        result = self.api_client.list_all_courses()
        if result is None:
            print("Error retrieving all courses.")
        else:
            print("\t".join([c['label'] for c in result]))

    def help_list_courses(self):
        print("Usage: list_courses")
        print("List all courses.")


    # TODO (rohany): error handling here!
    def do_list_assignments(self, course):
        # Parse the course info.
        if not course:
            print("Provide a course (number or label). list_assignments [course]")
        else:
            # TODO (rohany): verify that we are given a value course object.
            result = self.api_client.list_assignments(course)
            if result is None:
                print("Error retrieving all assignments.")
            else:
                print("\t".join([hw['name'] for hw in result]))

    def help_list_assignments(self):
        print("Usage: list_assignments [course]")
        print("List all assignments for a course.")


    def do_download_assignment(self, args):
        # TODO (rohany): perform better parsing of arguments
        args = args.split(" ")
        self.api_client.download_assignment(args[0], args[1])

    def help_download_assignment(self):
        print("Usage: download_assignment [course] [assignment]")
        print("Download handout materials for an assignment.")


    def do_submit_assignment(self, args):
        # TODO (rohany): perform better parsing of arguments
        args = args.split(" ")
        success, res_url = self.api_client.submit_assignment(args[0], args[1], args[2])
        if success:
            print("Assignment submitted successfully. Track your submission's status at the following url: {}".format(res_url))
        else:
            # TODO: have more descriptive error messages here.
            print("Something went wrong. Please try submitting on the Diderot website at: {}".format(self.url))
    
    def help_submit_assignment(self, args):
        print("Usage: submit_assignment [course] [assignment] [path to handin file]")
        print("Submit handin to Diderot for an assignment")


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