# diderot-cli

Command line interface to interact with [Diderot](http://www.umut-acar.org/diderot).

We welcome contributors! If you are interested in contributing, read CONTRIBUTING.md for some basic guidelines, and grab an issue, or submit your own! 

We thank William Paivine for his initial work on this project.

## Installation

To install the CLI, clone this repo. The CLI depends only on python's `requests` package, and requires python 3.6 or higher.

To install the requests package, use `pip3 install requests`.

## Basic Usage

Use the `diderot_student` or `diderot_admin` script depending on your use case. The `diderot_student` and `diderot_admin` scripts accept a `--url` flag, which is meant solely for development (this connects the CLI to a particular instance of Diderot which is different that `http://www.diderot.one`). The remaining arguments are managing credentials.

### Credential Management

Credentials are passed to the CLI in one of two ways. The first is to simply pass your credentials via the CLI using the `--username` and `--password` flags on the CLI. A more convenient way is to use a credentials file. The credential file format is simply a text file with your username on the first line and your password on the second. Use the --credentials argument to point the CLI towards a file containing your credentials. For easier usage, the CLI automatically looks at the file `~/.diderot/credentials` for a credentials file of this form. If this file exists, then the CLI will automatically log you in, and no credentials need to be explicitly provided to the CLI.

## Student Version

The student CLI contains basic commands to list, download, and submit assignments via the CLI.

The CLI supports the following student commands.

* `list_courses`
* `list_assignments`
* `download_assignment`
* `submit_assignment`

Please look at the Diderot Guide or use the CLI's help messages for more information about these commands.

## Admin Version

The admin CLI contains all the commands of the student CLI along with commands to create and update book components.

The CLI supports the following admin commands.

* `list_books`
* `list_parts`
* `list_chapters`
* `create_part`
* `create_chapter`
* `upload_chapter`
* `update_assignment`

Please look at the Diderot Guide or use the CLI's help messages for more information about these commands.

## Testing

The CLI is backed by a small suite of unit tests that try to attain as much coverage of the codebase as possible. The tests mock the Diderot webserver and test communication behavior between the CLI and Diderot. However, they are not a complete assertion that changes to the CLI are correct, and are intended more as a deterrent against behavior regression.

To run the tests, run `./test.py`, or `./test.py -v` for more verbose output.
