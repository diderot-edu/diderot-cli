# File contains API endpoint call wrappers for interacting
# with Diderot, to avoid complicating logic within the CLI.

import requests
import sys
import urllib.parse
import shutil
import os
import glob
import tempfile

class DiderotAPIInterface:
    def __init__(self, base_url):
        self.base_url = base_url
        self.logged_in = False
        self.connect()

    # TODO: integrate this into the other functions
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
                print("Error: unable to connect to Diderot (error 404)!")
                sys.exit(0)
            elif code >= 500:
                print("Server failed to fulfill request for main page. (Code: {})".format(code))
                sys.exit(0)
        self.csrftoken = self.client.cookies['csrftoken']

    def login(self, username, password):
        if self.logged_in:
            return True
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
                print("Error: unable to connect to Diderot (error 404)!")
                sys.exit(0)
            elif code >= 500:
                print("Server failed to fulfill request for main page. (Code: {})".format(code))
                sys.exit(0)
            elif code == 200:
                print("Authentication failed. Your credentials might be incorrect.")
                self.logged_in = False
                return False
        self.csrftoken = self.client.cookies['csrftoken']
        print("Successfully logged in to Diderot.")
        self.logged_in = True
        return True

    def logout(self):
        if not self.logged_in:
            return True
        logout_url = urllib.parse.urljoin(self.base_url, "login/logout/")
        self.client.get(logout_url)
        self.logged_in = False
        print("Successfully logged out of Diderot.")
        return True

    # TODO: what is good error handling here?
    def list_all_courses(self):
        if not self.logged_in:
            return None
        list_courses_url = urllib.parse.urljoin(self.base_url, 'courses/api/courses/')
        headers = {'X-CSRFToken' : self.csrftoken}
        response = self.client.get(list_courses_url, headers=headers)
        if response.status_code == 200:
            return response.json()
        return None


    def list_assignments(self, course_label):
        if not self.logged_in:
            return None

        list_assignments_url = urllib.parse.urljoin(self.base_url, 'code-homeworks/api/codehomeworks/')
        headers = {'X-CSRFToken' : self.csrftoken}
        response = self.client.get(list_assignments_url, headers=headers, params={'course__label' : course_label})
        if response.status_code == 200:
            return response.json()
        return None

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
        if not self.logged_in:
            return False, None

        get_assignment_info_url = urllib.parse.urljoin(self.base_url, 'code-homeworks/api/codehomeworks/')
        headers = {'X-CSRFToken' : self.csrftoken}
        response = self.client.get(get_assignment_info_url, headers=headers, params={'course__label' : course, 'name' : homework})
        if response.status_code != 200:
            # TODO: better error handling?
            return None
        resp_body = response.json()
        if len(resp_body) != 1:
            # TODO: better error handling?
            return None
        homework_pk = resp_body[0]['id']
        submit_assignment_url = urllib.parse.urljoin(self.base_url, 'code-homeworks/view-code-homework/')
        # TODO (rohany): return more information in the response, such as:
        # homework due date, whether its the latest homework or not, etc.
        # All this extra stuff that the student would need to confirm
        # if they want to submit to this assignment.
        full_path = self.expand_file_path(filepath)
        # TODO: Support other types of file handins (single file, etc.)
        response = self.client.post(submit_assignment_url, headers=headers, files={'submission_tar' : open(full_path, 'rb')}, params={'hw_pk' : homework_pk})

        # TODO: return some more descriptive output.
        return response.status_code == 200, submit_assignment_url + "?hw_pk={}".format(homework_pk)

    def download_assignment(self, course, homework):
        if self.logged_in:
            course_info_url = urllib.parse.urljoin(self.base_url, 'courses/api/courses/')
            homework_info_url = urllib.parse.urljoin(self.base_url, 'code-homeworks/api/codehomeworks/')
            headers = {'X-CSRFToken' : self.csrftoken}

            response = self.client.get(course_info_url, headers=headers, params={'label' : course})
            if response.status_code != 200:
                return None
            if len(response.json()) != 1:
                return None
            course_info = response.json()[0]

            response = self.client.get(homework_info_url, headers=headers, params={'course__label' : course, 'name' : homework})
            if response.status_code != 200:
                return None
            if len(response.json()) != 1:
                return None
            hw_info = response.json()[0]

            base_path = "http://s3.amazonaws.com/" + course_info['s3_autograder_bucket'] + "/" + hw_info['name'] + "/"
            writeup_path = base_path + 'writeup.pdf'
            handout_path = base_path + "{}-handout-{}.tgz".format(course_info['number'], hw_info['number'])

            for p in [writeup_path, handout_path]:
                self.download_file_helper(p)

    def update_assignment(self, course, homework, args):
        get_assignment_info_url = urllib.parse.urljoin(self.base_url, 'code-homeworks/api/codehomeworks/')
        headers = {'X-CSRFToken' : self.csrftoken}
        response = self.client.get(get_assignment_info_url, headers=headers, params={'course__label' : course, 'name' : homework})
        if response.status_code != 200:
            # TODO: better error handling?
            return False
        resp_body = response.json()
        if len(resp_body) != 1:
            # TODO: better error handling?
            return False
        homework_pk = resp_body[0]['id']

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
        update_url = urllib.parse.urljoin(self.base_url, 'code-homeworks/admin/upload-files/')
        self.response = self.client.post(update_url, headers=headers, files=files, params={'hw_pk' : homework_pk})
        return response.status_code == 200

    def list_books(self, course=None):
        get_books_url = urllib.parse.urljoin(self.base_url, 'books/api/books/')
        headers = {'X-CSRFToken' : self.csrftoken}
        params = {}
        if course is not None:
            params['course__label'] = course
        response = self.client.get(get_books_url, headers=headers, params=params)
        if response.status_code != 200:
            return None
        return response.json()

    def update_book(self, book, chapter, args):
        get_books_url = urllib.parse.urljoin(self.base_url, 'books/api/books/')
        headers = {'X-CSRFToken' : self.csrftoken}
        params = {'label' : book}
        result = self.verify_singleton_response(self.client.get(get_books_url, headers=headers, params=params))
        if result is None:
            return False
        book_pk = result['id']

        update_url = urllib.parse.urljoin(self.base_url, 'books/manage_book/')
        update_data = {'pk' : book_pk}
        update_params = {'kind' : 'upload content'}
        files = {}
        if args.pdf is not None:
            if not args.pdf.lower().endswith(".pdf"):
                print("PDF argument must be a PDF file.")
                return False
            files['input_file_pdf'] = open(self.expand_file_path(args.pdf), 'rb')
            if args.video_url is not None:
                update_params['video_url_pdf'] = args.video_url
        elif args.slides is not None:
            if not args.slides.lower().endswith(".pdf"):
                print("Slides argument must be a PDF file.")
                return False
            files['input_file_slide'] = open(self.expand_file_path(args.slides), 'rb')
            if args.video_url is not None:
                update_params['video_url_slide'] = args.video_url
        elif args.xml is not None:
            if not (args.xml.lower().endswith(".xml") or args.xml.lower().endswith(".mlx")):
                print("XML argument must be an XML or MLX file.")
                return False
            files['input_file_xml'] = open(self.expand_file_path(args.xml), 'rb')
            # TODO: because Diderot wants only the base names, I think
            # we are going to have to move into a temp directory,
            # copy all the files into there, add them all, and then move back.
            if args.images is not None:
                tmpDir = tempfile.mkdtemp()
                curPath = os.getcwd()
                os.chdir(tmpDir)
                for fg in args.images:
                    files = glob.glob(fg)
                    for f in files:
                        full_path = self.expand_file_path(f)
                        shutil.copyfile(full_path, os.path.basename(full_path))
                build = []
                for f in os.listdir(os.cwd()):
                    build.append(open(f, 'rb'))
                files['image'] = build

        # verify that the input arguments are correct.
        response = self.client.post(update_url, headers=headers, data=update_data, params=update_params, files=files)
        if response.status != 200:
            print(response)
            return False
        return True
