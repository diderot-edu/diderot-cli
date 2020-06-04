# File contains API endpoint call wrappers for interacting
# with Diderot, to avoid complicating logic within the CLI.

import requests
import sys
import urllib.parse
import shutil
import os
import glob
import tempfile
import time

from contextlib import ExitStack
from pathlib import Path


def exit_with_error(error_msg):
    print(error_msg)
    sys.exit(1)

class DiderotAPIInterface:
    def __init__(self, base_url):
        self.base_url = base_url
        self.connect()

    def verify_singleton_response(self, response):
        if response.status_code != 200:
            return None
        if len(response.json()) != 1:
            return None
        return response.json()[0]

    # Utility functions here. If this gets too large, pull into its own file.
    def expand_file_path(self, path):
        return os.path.abspath(os.path.expandvars(os.path.expanduser(path)))

    def connect(self):
        self.client = requests.session()
        main_page = self.client.get(self.base_url)
        code = main_page.status_code
        if not code == 200:
            if code == 404:
                exit_with_error("Error: unable to connect to Diderot (error 404)!")
            elif code >= 500:
                exit_with_error("Server failed to fulfill request for main page. (Code: {})".format(code))
        self.csrftoken = self.client.cookies['csrftoken']

    def login(self, username, password, shouldPrint=True):
        login_data = {'username' : username,
                      'password' : password,
                      'csrfmiddlewaretoken': self.csrftoken,
                      'next': '/courses/'}
        login_url = urllib.parse.urljoin(self.base_url, "login/login/?next=/courses/")
        r = self.client.post(login_url, data=login_data)
        if len(r.history) > 0:
            code = r.history[0].status_code
        else:
            code = r.status_code

        if not code == 302:
            if code == 404:
                exit_with_error("Error: unable to connect to Diderot (error 404)!")
            elif code >= 500:
                exit_with_error("Server failed to fulfill request for main page. (Code: {})".format(code))
            elif code == 200:
                exit_with_error("Authentication failed. Your credentials might be incorrect.")
                return False
        self.csrftoken = self.client.cookies['csrftoken']
        if shouldPrint:
            print("Successfully logged in to Diderot.")
        return True

    def logout(self):
        logout_url = urllib.parse.urljoin(self.base_url, "login/logout/")
        self.client.get(logout_url)
        print("Successfully logged out of Diderot.")
        return True

    def verify_course_label(self, course_label):
        headers = {'X-CSRFToken' : self.csrftoken}
        list_courses_url = urllib.parse.urljoin(self.base_url, 'api/courses/')
        response = self.client.get(list_courses_url, headers=headers, params={'label': course_label})
        result = self.verify_singleton_response(response)
        if result is None:
            print(f"The requested course label ({course_label}) does not exist. You might not be a member of the requested course if it exists.")
            return False
        return True

    # TODO (rohany): Refactor existing code to use these checks.
    def is_booklet(self, course, book):
        get_books_url = urllib.parse.urljoin(self.base_url, 'api/books/')
        headers = {'X-CSRFToken' : self.csrftoken}
        params = {'course__label' : course, 'label' : book}
        response = self.client.get(get_books_url, headers=headers, params=params)
        res = self.verify_singleton_response(response)
        if res is None:
            print("Input book not found.")
            return None
        return bool(res['is_booklet'])

    def chapter_exists(self, course, book, chapter_num):
        # TODO (rohany): When we can filter by course label and book label for chapters,
        #  these additional accesses can be removed.
        if not self.verify_course_label(course):
            return False
        get_books_url = urllib.parse.urljoin(self.base_url, 'api/books/')
        headers = {'X-CSRFToken' : self.csrftoken}
        params = {'label' : book, 'course__label' : course}
        result = self.verify_singleton_response(self.client.get(get_books_url, headers=headers, params=params))
        if result is None:
            print("Input book not found.")
            return False
        book_pk = result['id']
        course_pk = result['course']
        get_chapters_url = urllib.parse.urljoin(self.base_url, 'api/chapters/')
        params = {'course__id' : course_pk, 'book__id' : book_pk, 'rank': chapter_num}
        result = self.verify_singleton_response(self.client.get(get_chapters_url, headers=headers, params=params))
        return result is not None

    def list_all_courses(self):
        list_courses_url = urllib.parse.urljoin(self.base_url, 'api/courses/')
        headers = {'X-CSRFToken' : self.csrftoken}
        response = self.client.get(list_courses_url, headers=headers)
        if response.status_code != 200:
            print("Unable to make a request to Diderot.")
            return None
        return response.json()


    def list_assignments(self, course_label):
        headers = {'X-CSRFToken' : self.csrftoken}
        if not self.verify_course_label(course_label):
            return None
        list_assignments_url = urllib.parse.urljoin(self.base_url, 'api/codehomeworks/')
        response = self.client.get(list_assignments_url, headers=headers, params={'course__label' : course_label})
        if response.status_code != 200:
            print("Unable to make a request to Diderot.")
            return None
        return response.json()

    def download_file_helper(self, url):
        r = requests.get(url, stream=True)
        if r.status_code == 200:
            local_filename = url.split('/')[-1]
            if os.path.isfile(local_filename):
                print('There is already a file called {}, so I won\'t download a new one.'
                      ' Rename the old one and please try again'.format(local_filename))
                return False
            print('Trying to download file to {}'.format(local_filename))
            with open(local_filename, 'wb') as f:
                shutil.copyfileobj(r.raw, f)
            return True
        return False

    def submit_assignment(self, course, homework, filepath):
        if not self.verify_course_label(course):
            return False, None

        get_assignment_info_url = urllib.parse.urljoin(self.base_url, 'api/codehomeworks/')
        headers = {'X-CSRFToken' : self.csrftoken}
        response = self.client.get(get_assignment_info_url, headers=headers, params={'course__label' : course, 'name' : homework})
        result = self.verify_singleton_response(response)
        if result is None:
            print("Invalid homework name.")
            return False, None
        homework_pk = result['id']
        handin_type = result['handin_style']
        course_pk = result['course']
        submit_assignment_url = urllib.parse.urljoin(self.base_url, 'course/{}/code-homeworks/view-code-homework/'.format(course_pk))
        # TODO (rohany): return more information in the response, such as:
        # homework due date, whether its the latest homework or not, etc.
        # All this extra stuff that the student would need to confirm
        # if they want to submit to this assignment.
        full_path = self.expand_file_path(filepath)
        if not os.path.exists(full_path):
            print("Input file does not exist.")
            return False, None

        f = open(full_path, 'rb')
        files = {}
        if handin_type == 'TR':
            files['submission_tar'] = f
        elif handin_type == 'FU':
            files['submission_files'] = f
        else:
            print("For copy-paste or per problem copy-paste handins, use the web interface.")
            return False, None
        response = self.client.post(submit_assignment_url, headers=headers, files=files, params={'hw_pk' : homework_pk})
        f.close()

        # TODO: return some more descriptive output.
        return response.status_code == 200, submit_assignment_url + "?hw_pk={}".format(homework_pk)

    def download_assignment(self, course, homework):
        if not self.verify_course_label(course):
            return None
        course_info_url = urllib.parse.urljoin(self.base_url, 'api/courses/')
        homework_info_url = urllib.parse.urljoin(self.base_url, 'api/codehomeworks/')
        headers = {'X-CSRFToken' : self.csrftoken}
        response = self.client.get(course_info_url, headers=headers, params={'label' : course})
        result = self.verify_singleton_response(response)
        if result is None:
            print("Invalid course label")
            return None
        course_info = result

        response = self.client.get(homework_info_url, headers=headers, params={'course__label' : course, 'name' : homework})
        result = self.verify_singleton_response(response)
        if result is None:
            print("Invalid homework name.")
            return None
        hw_info = result

        base_path = "http://s3.amazonaws.com/" + course_info['s3_autograder_bucket'] + "/" + hw_info['name'] + "/"
        writeup_path = base_path + 'writeup.pdf'
        handout_path = base_path + "{}-handout-{}.tgz".format(course_info['number'], hw_info['name'])

        for p in [writeup_path, handout_path]:
            self.download_file_helper(p)
        return True

    def update_assignment(self, course, homework, args):
        get_assignment_info_url = urllib.parse.urljoin(self.base_url, 'api/codehomeworks/')
        headers = {'X-CSRFToken' : self.csrftoken}
        if not self.verify_course_label(course):
            return False
        response = self.client.get(get_assignment_info_url, headers=headers, params={'course__label' : course, 'name' : homework})
        result = self.verify_singleton_response(response)
        if result is None:
            print("Invalid homework name.")
            return False
        homework_pk = result['id']
        course_pk = result['course']

        # send a request to the UploadCodeLabFiles view with the target
        # files in the request.
        files = {}
        if args.autograde_tar is not None:
            files['autograde-tar'] = open(self.expand_file_path(args.autograde_tar), 'rb')
        if args.autograde_makefile is not None:
            files['autograde-makefile'] = open(self.expand_file_path(args.autograde_makefile), 'rb')
        if args.handout is not None:
            files['handout'] = open(self.expand_file_path(args.handout), 'rb')
        if args.writeup is not None:
            files['writeup'] = open(self.expand_file_path(args.writeup), 'rb')

        if len(files) == 0:
            return True

        headers = {'X-CSRFToken' : self.csrftoken}
        update_url = urllib.parse.urljoin(self.base_url, 'course/{}/code-homeworks/admin/upload-files/'.format(course_pk))
        response = self.client.post(update_url, headers=headers, files=files, params={'hw_pk' : homework_pk})
        for _,v in files.items():
            v.close()
        return response.status_code == 200

    def list_books(self, course, all=False):
        get_books_url = urllib.parse.urljoin(self.base_url, 'api/books/')
        headers = {'X-CSRFToken' : self.csrftoken}
        params = {}
        if not all:
            if course is None:
                print("A course label is required if not listing all books.")
                return None
            params['course__label'] = course
            if not self.verify_course_label(course):
                return None
        bookresponse = self.client.get(get_books_url, headers=headers, params=params)
        if bookresponse.status_code != 200:
            return None
        if not all:
            return bookresponse.json()
        else:
            # filter the books by what courses can be seen.
            courses = self.list_all_courses()
            # turn it into a map
            course_dict = dict([(course['id'], course) for course in courses])
            return [book for book in bookresponse.json() if book['course'] in course_dict]

    def list_parts(self, course, book):
        if not self.verify_course_label(course):
            return None
        get_books_url = urllib.parse.urljoin(self.base_url, 'api/books/')
        headers = {'X-CSRFToken' : self.csrftoken}
        params = {'course__label' : course, 'label' : book}
        response = self.client.get(get_books_url, headers=headers, params=params)
        res = self.verify_singleton_response(response)
        if res is None:
            print("Input book not found.")
            return None
        book_pk = res['id']

        get_parts_url = urllib.parse.urljoin(self.base_url, 'api/parts/')
        params = {'book__id' : book_pk}
        response = self.client.get(get_parts_url, headers=headers, params=params)
        if response.status_code != 200:
            print("Parts request to diderot failed.")
            return None
        return response.json()

    def list_chapters(self, course, book):
        if not self.verify_course_label(course):
            return None
        get_books_url = urllib.parse.urljoin(self.base_url, 'api/books/')
        headers = {'X-CSRFToken' : self.csrftoken}
        params = {'course__label' : course, 'label' : book}
        response = self.client.get(get_books_url, headers=headers, params=params)
        res = self.verify_singleton_response(response)
        if res is None:
            print("Input book not found.")
            return None
        book_pk = res['id']

        get_chapters_url = urllib.parse.urljoin(self.base_url, 'api/chapters/')
        params = {'course__label' : course, 'book__id' : book_pk}
        response = self.client.get(get_chapters_url, headers=headers, params=params)
        if response.status_code != 200:
            print("Chapters request to diderot failed.")
            return None
        return response.json()

    def create_part(self, args):
        if not self.verify_course_label(args.course):
            return False
        get_books_url = urllib.parse.urljoin(self.base_url, 'api/books/')
        headers = {'X-CSRFToken' : self.csrftoken}
        params = {'course__label' : args.course, 'label' : args.book}
        response = self.client.get(get_books_url, headers=headers, params=params)
        res = self.verify_singleton_response(response)
        if res is None:
            print("Input book not found.")
            return False
        book_pk = res['id']
        course_pk = res['course']

        if bool(res['is_booklet']):
            print("Part creation is disallowed on booklets.")
            return False

        get_parts_url = urllib.parse.urljoin(self.base_url, 'api/parts/')
        params = {'book__id' : book_pk, 'rank' : args.number}
        response = self.client.get(get_parts_url, headers=headers, params=params)
        if response.status_code != 200:
            print("Parts request to diderot failed.")
            return False
        if len(response.json()) != 0:
            print("Existing part for Course: {}, Book: {}, and Number: {} found.".format(args.course, args.book, args.number))
            return False

        # create the part now.
        create_url = urllib.parse.urljoin(self.base_url, 'course/{}/books/manage_book/{}/'.format(course_pk, book_pk))
        create_params = {'kind': 'create part', 'title': args.title, 'rank' : args.number}
        if args.label is not None:
            create_params['label'] = args.label

        response = self.client.post(create_url, headers=headers, data=create_params)
        if response.status_code != 200:
            print("Part creation request was not successful.")
            return False
        return True

    def create_chapter(self, args):
        if not self.verify_course_label(args.course):
            return False
        get_books_url = urllib.parse.urljoin(self.base_url, 'api/books/')
        headers = {'X-CSRFToken' : self.csrftoken}
        params = {'course__label' : args.course, 'label' : args.book}
        response = self.client.get(get_books_url, headers=headers, params=params)
        res = self.verify_singleton_response(response)
        if res is None:
            print("Input book not found.")
            return None
        book_pk = res['id']
        course_pk = res['course']

        get_parts_url = urllib.parse.urljoin(self.base_url, 'api/parts/')
        if bool(res['is_booklet']):
            params = {'book__id' : book_pk}
        else:
            if args.part is None:
                print('--part must be set. {} is not a booklet.'.format(args.book))
                return None
            params = {'book__id' : book_pk, 'rank' : args.part}

        # verify that the desired part exists.
        result = self.verify_singleton_response(self.client.get(get_parts_url, headers=headers, params=params))
        if result is None:
            print("Input part not found.")
            return False
        part_pk = result['id']

        # see if a chapter like this exists already.
        get_chapters_url = urllib.parse.urljoin(self.base_url, 'api/chapters/')
        params = {'course__id' : course_pk, 'book__id' : book_pk, 'rank' : args.number}
        response = self.client.get(get_chapters_url, headers=headers, params=params)
        if response.status_code != 200:
            print("Chapters request to diderot failed.")
            return None
        if len(response.json()) != 0:
            print("Existing chapter for Course: {}, Book: {} and Number: {} found.".format(args.course, args.book, args.number))
            return False

        # actually create the chapter now.
        create_url = urllib.parse.urljoin(self.base_url, 'course/{}/books/manage_book/{}/'.format(course_pk, book_pk))
        create_params = {'kind': 'create chapter', 'part_pk' : part_pk, 'rank' : args.number}
        if args.title is not None:
            create_params['title'] = args.title
        if args.label is not None:
            create_params['label'] = args.label

        response = self.client.post(create_url, headers=headers, data=create_params)
        if response.status_code != 200:
            print("Chapter creation request was not successful.")
            return False

        return True

    # TODO (rohany): There is some gross code duplication happening here.
    # Figure out if theres a way we can refactor getting the chapter pk here.
    # Probably can do something like dispatch to a more specific function
    # set given the book, course and chapter pk's.
    def release_unrelease_chapter(self, course, book, args, release=True):
        if not self.verify_course_label(course):
            return False
        # get the book and course primary key
        get_books_url = urllib.parse.urljoin(self.base_url, 'api/books/')
        headers = {'X-CSRFToken' : self.csrftoken}
        params = {'label' : book, 'course__label' : course}
        result = self.verify_singleton_response(self.client.get(get_books_url, headers=headers, params=params))
        if result is None:
            print("Input book not found.")
            return False
        book_pk = result['id']
        course_pk = result['course']
        # get the primary key of the chapter
        get_chapters_url = urllib.parse.urljoin(self.base_url, 'api/chapters/')
        params = {'course__id' : course_pk, 'book__id' : book_pk}
        if args.chapter_number is not None:
            params['rank'] = args.chapter_number
        elif args.chapter_label is not None:
            params['label'] = args.chapter_label
        else:
            print("Chapter label or Chapter number must be provided.")
            return False
        result = self.verify_singleton_response(self.client.get(get_chapters_url, headers=headers, params=params))
        if result is None:
            print("Input chapter not found.")
            return False
        chapter_pk = result['id']

        release_url = urllib.parse.urljoin(self.base_url, 'course/{}/books/manage_book/{}/'.format(course_pk, book_pk))
        release_params = {'chapter_pk' : chapter_pk}
        if release:
            release_params['kind'] = 'release'
        else:
            release_params['kind'] = 'unrelease'

        response = self.client.post(release_url, headers=headers, data=release_params)
        return response.status_code == 200

    def upload_chapter(self, course, book, args, sleep_time=5):
        if not self.verify_course_label(course):
            return False
        # get the book and course primary key
        get_books_url = urllib.parse.urljoin(self.base_url, 'api/books/')
        headers = {'X-CSRFToken' : self.csrftoken}
        params = {'label' : book, 'course__label' : course}
        result = self.verify_singleton_response(self.client.get(get_books_url, headers=headers, params=params))
        if result is None:
            print("Input book not found.")
            return False
        book_pk = result['id']
        course_pk = result['course']

        # get the primary key of the chapter
        get_chapters_url = urllib.parse.urljoin(self.base_url, 'api/chapters/')
        params = {'course__id' : course_pk, 'book__id' : book_pk}
        if args.chapter_number is not None:
            params['rank'] = args.chapter_number
        elif args.chapter_label is not None:
            params['label'] = args.chapter_label
        else:
            print("Chapter label or Chapter number must be provided.")
            return False
        result = self.verify_singleton_response(self.client.get(get_chapters_url, headers=headers, params=params))
        if result is None:
            print("Input chapter not found.")
            return False
        chapter_pk = result['id']

        update_url = urllib.parse.urljoin(self.base_url, 'course/{}/books/manage_book/{}/'.format(course_pk, book_pk))
        update_params = {'kind': 'upload content', 'chapter_pk' : chapter_pk}

        # Populate the input set of files.
        files = []
        if args.pdf is not None:
            if not args.pdf.lower().endswith(".pdf"):
                print("PDF argument must be a PDF file.")
                return False
            files.append(('input_file_pdf', Path(args.pdf)))
            if args.video_url is not None:
                update_params['video_url_pdf'] = args.video_url
        elif args.slides is not None:
            if not args.slides.lower().endswith(".pdf"):
                print("Slides argument must be a PDF file.")
                return False
            files.append(('input_file_slide', Path(args.slides)))
            if args.video_url is not None:
                update_params['video_url_slide'] = args.video_url
        elif args.xml is not None:
            if not (args.xml.lower().endswith(".xml") or args.xml.lower().endswith(".mlx")):
                print("XML argument must be an XML or MLX file.")
                return False
            files.append(('input_file_xml', Path(args.xml)))
            if args.attach is not None:
                for fg in args.attach:
                    base_path = Path(fg)
                    file_glob = glob.glob(self.expand_file_path(fg))
                    if not base_path.exists() and len(file_glob) == 0:
                        print("Warning: cannot find file {}. Skipping.".format(fg))
                        
                        continue
                    for g in file_glob:
                        f = Path(g).expanduser()
                        if f.is_dir():
                            # If it is a directory, include all children.
                            files.extend([("image", m) for m in f.glob("**/*")])
                        else:
                            # If it is a file, add it directly.
                            files.append(("image", f))
            if args.xml_pdf is not None:
                files.append(('input_file_xml_pdf', Path(args.xml_pdf)))

        for _, p in files:
            print("Uploading file:", p.name)

        with ExitStack() as stack:
            opened_files = [(typ, (path.name, stack.enter_context(
                path.expanduser().open('rb')))) for typ, path in files]
            response = self.client.post(update_url, headers=headers, files=opened_files, data=update_params)

        if response.status_code != 200:
            print("Chapter upload request was not successful.")
            return False

        # wait until the book becomes unlocked
        while True:
            print("Waiting for book upload to complete...")
            time.sleep(sleep_time)
            params = {'id' : book_pk}
            result = self.verify_singleton_response(self.client.get(get_books_url, headers=headers, params=params))
            if result is None:
                print("Book primary keys must be unique.")
                return False
            if not bool(result['is_locked']):
                break

        # get back error + warning information from uploading!
        params = {'id' : chapter_pk}
        result = self.verify_singleton_response(self.client.get(get_chapters_url, headers=headers, params=params))
        if result is None:
            print("Chapter primary keys must be unique.")
            return False

        warnings = result['upload_warnings']
        if len(warnings) != 0:
            print(warnings)
        errors = result['upload_errors']
        if len(errors) != 0:
            print(errors)
            return False

        return True
