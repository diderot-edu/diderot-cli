# File contains API endpoint call wrappers for interacting
# with Diderot, to avoid complicating logic within the CLI.

import requests
import sys
import urllib.parse
import shutil
import os

class DiderotAPIInterface:
    def __init__(self, base_url):
        self.base_url = base_url
        self.logged_in = False
        self.connect()

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
        list_courses_url = urllib.parse.urljoin(self.base_url, "cli/list-courses/")
        headers = {'X-CSRFToken' : self.csrftoken}
        response = self.client.post(list_courses_url, headers=headers)
        if response.status_code == 200:
            return response.json()["courses"]
        return None

    def list_assignments(self, course_label):
        if not self.logged_in:
            return None
        list_assignments_url = urllib.parse.urljoin(self.base_url, "cli/list-assignments/")
        headers = {'X-CSRFToken' : self.csrftoken}
        response = self.client.post(list_assignments_url, headers=headers, data={'course_label' : course_label})
        if response.status_code == 200:
            return response.json()["assignments"]
        print(response.status_code)
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
            return None
        # submit_assignment_url = urllib.
        pass

    def download_assignment(self, course, homework):
        if self.logged_in:
            download_files_url = urllib.parse.urljoin(self.base_url, "cli/download-assignment/")
            headers = {'X-CSRFToken' : self.csrftoken}
            response = self.client.post(download_files_url, headers=headers, data={'course_label' : course, 'homework_name' : homework})
            if response.status_code == 200:
                for v in response.json().values():
                    self.download_file_helper(v)

