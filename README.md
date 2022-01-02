![Build Status](https://codebuild.us-east-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiZ2NjRndxM3AybjBlRXYvWDdrOWFxTVIrMkkxa3NTRmkrb3VhUVF1eS9tT3E5VEJOVHhST0lHcWcraE9MTkFNNGNNODI0YUFCaXdkYVFnQmx1UDFPb2FzPSIsIml2UGFyYW1ldGVyU3BlYyI6Ilg4emtuM3V0bG5WVDBDMTMiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=master)

# diderot-cli

Command line interface to interact with [Diderot](http://www.diderot.one).

We welcome contributors! If you are interested in contributing, read CONTRIBUTING.md for some basic guidelines, and grab an issue, or submit your own! 

We thank William Paivine for his initial work on this project.

## Installation

To install the CLI, either clone this repo and run `make install`, or download the pre-packaged `wheel` file and run `pip install path/to/didert_cli-VERSION-[...].whl`. It requires python 3.7 or higher.
The dependencies are automatically installed if not present.

If you do not wish to install this package globally, you can create a virtualenv, install the dependencies manually wih `pip install -r requirements.txt` (may include development dependencies as well) and use the `diderot`, `diderot_admin` or `diderot_student` scripts at the root of this project.

## Basic Usage

Run `diderot admin --help` or `diderot student --help` to see the available commands, depending on your use case

For more details see [the guide](https://www.diderot.one/course/15/chapters/736/).

## Environment

The cli accepts the following options as environment variables:

* `DIDEROT_USER` -> instead of `--username`
* `DIDEROT_PASSWORD` -> instead of `--password`
* `DIDEROT_URL` -> instead of `--url`
* `DEBUG` -> instead of `--debug`

### Credential Management

Credentials are passed to the CLI in one of three ways.
The first is to simply pass your credentials via the CLI using the `--username` and `--password` flags on the CLI.
A more convenient way is to use a credentials file. The credential file format is simply a text file with your username on the first line and your password on the second. Use the `--credentials` argument to point the CLI towards a file containing your credentials. For easier usage, the CLI automatically looks at the file `~/private/.diderot/credentials` and then `~/.diderot/credentials` for a credentials file of this form. If this file exists, then the CLI will automatically log you in, and no credentials need to be explicitly provided to the CLI. An important note is that your credentials file must have only "owner can read and write" permissions. To do this, run `chmod 600 <credentials file>`.
If you omit the `--username`/`--password` pair **and** the `--credentials` flag, you will be prompted for them when running the command. The password is not echoed back to the terminal when typing.

## Student Version

The student CLI contains basic commands to list, download, and submit assignments via the CLI.

The CLI supports the following student commands.

* `download-assignment`
* `list-assignments`
* `list-courses`
* `submit-assignment`

Please look at the Diderot Guide or use the CLI's help messages for more information about these commands.

## Admin Version

The admin CLI contains all the commands of the student CLI along with commands to create and update book components.

The CLI supports the following admin commands.

* `create-book`
* `create-chapter`
* `create-part`
* `download-assignment`
* `list-assignments`
* `list-books`
* `list-chapters`
* `list-courses`
* `list-parts`
* `publish-chapter`
* `retract-chapter`
* `set-publish-date`
* `submit-assignment`
* `update-assignment`
* `upload-book`
* `upload-chapter`

Please look at the Diderot Guide or use the CLI's help messages for more information about these commands.

## Testing

The CLI is backed by a small suite of unit tests that try to attain as much coverage of the codebase as possible. The tests mock the Diderot webserver and test communication behavior between the CLI and Diderot. However, they are not a complete assertion that changes to the CLI are correct, and are intended more as a deterrent against behavior regression.

To run the tests, run `make test`.
