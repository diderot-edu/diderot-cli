from cli_utils import APIError, singleton_or_none

# URL constants for API access.
COURSE_API = "/api/courses/"
LAB_API = "/frontend-api/courses/{}/codelabs/"
BOOK_API = "/api/books/"
PARTS_API = "/api/parts/"
CHAPTERS_API = "/api/chapters/"
MANAGE_BOOK_API = "/course/{}/books/manage_book/{}/"
MANAGE_BOOK_API_NEW = "/frontend-api/courses/{course_id}/books/{book_id}/"
SUBMIT_ASSIGNMENT_API = "/frontend-api/courses/{}/codelabs/{}/submissions/create_and_submit/"
UPLOAD_FILES_API = "/frontend-api/courses/{}/codelabs/{}/"


class Course:
    def __init__(self, client, label):
        self.client = client
        self.label = label
        self.pk = None
        self.autograder_bucket = None
        self.number = None
        self._verify()

    def _verify(self):
        response = self.client.get(COURSE_API, params={"label": self.label})
        result = singleton_or_none(response)
        if result is None:
            raise APIError(
                "The requested course label does not exist. "
                "You might not be a member of the requested "
                "course if it exists."
            )
        self.pk = result["id"]
        self.autograder_bucket = result["s3_autograder_bucket"]
        self.number = result["number"]

    @staticmethod
    def list(client):
        return client.get(COURSE_API).json()


class Lab:
    def __init__(self, course, name):
        self.course = course
        self.name = name
        self.client = course.client
        self.pk = None
        self.uuid = ""
        self._verify()

    def _verify(self):
        params = {
            "name": self.name,
        }
        response = self.client.get(LAB_API.format(self.course.pk), params=params)
        result = singleton_or_none(response)
        if result is None:
            raise APIError("Invalid homework name.")
        self.pk = result["id"]
        self.uuid = result["uuid"]

    @staticmethod
    def list(course):
        return course.client.get(LAB_API.format(course.pk)).json()


class Book:
    def __init__(self, course, label):
        self.course = course
        self.client = course.client
        self.label = label
        self.pk = None
        self._verify()

    def _verify(self):
        params = {
            "course__label": self.course.label,
            "label": self.label,
        }
        response = self.client.get(BOOK_API, params=params)
        result = singleton_or_none(response)
        if result is None:
            raise APIError("Input book not found.")
        self.pk = result["id"]
        self.is_booklet = bool(result["is_booklet"])

    @staticmethod
    def list(client, course=None):
        params = {}
        if course is not None:
            params["course__label"] = course.label
        return client.get(BOOK_API, params=params).json()

    @staticmethod
    def check_is_locked(client, id):
        response = client.get(BOOK_API, params={"id": id})
        result = singleton_or_none(response)
        return bool(result["is_locked"])


class Part:
    def __init__(self, course, book, number):
        self.course = course
        self.book = book
        self.client = course.client
        self.pk = None
        self._verify(number)

    def _verify(self, number):
        # If we have a booklet, then don't look at number.
        if self.book.is_booklet:
            params = {"book__id": self.book.pk}
        else:
            params = {"book__id": self.book.pk, "rank": number}
        response = self.client.get(PARTS_API, params=params)
        result = singleton_or_none(response)
        if result is None:
            raise APIError("Input part not found.")
        self.pk = result["id"]

    @staticmethod
    def create(course, book, title, number, label):
        params = {
            "kind": "create part",
            "title": title,
            "rank": number,
        }
        if label is not None:
            params["label"] = label
        course.client.post(MANAGE_BOOK_API.format(course.pk, book.pk), data=params)

    @staticmethod
    def exists(course, book, number):
        params = {
            "book__id": book.pk,
            "rank": number,
        }
        response = course.client.get(PARTS_API, params=params)
        return len(response.json()) != 0

    @staticmethod
    def list(course, book):
        return course.client.get(PARTS_API, params={"book__id": book.pk}).json()


class Chapter:
    def __init__(self, course, book, number, label):
        self.course = course
        self.book = book
        self.client = course.client
        self.pk = None
        self.number = None
        self.label = None
        self._verify(number, label)

    def _verify(self, number, label):
        params = {
            "course__id": self.course.pk,
            "book__id": self.book.pk,
        }
        if number is not None:
            params["rank"] = number
        elif label is not None:
            params["label"] = label
        else:
            raise APIError("Chapter label or Chapter number must be provided.")
        response = self.client.get(CHAPTERS_API, params=params)
        result = singleton_or_none(response)
        if result is None:
            raise APIError("Input chapter not found.")
        self.pk = result["id"]
        self.number = result["rank"]
        self.label = result["label"]

    @staticmethod
    def exists(course, book, number):
        params = {
            "course__id": course.pk,
            "book__id": book.pk,
            "rank": number,
        }
        response = course.client.get(CHAPTERS_API, params=params)
        return len(response.json()) != 0

    @staticmethod
    def create(course, book, part, number, title, label):
        params = {
            "kind": "create chapter",
            "part_pk": part.pk,
            "rank": number,
        }
        if title is not None:
            params["title"] = title
        if label is not None:
            params["label"] = label
        course.client.post(MANAGE_BOOK_API.format(course.pk, book.pk), data=params)

    @staticmethod
    def list(course, book):
        params = {
            "course__label": course.label,
            "book__id": book.pk,
        }
        return course.client.get(CHAPTERS_API, params=params).json()

    @staticmethod
    def get_warnings_and_errors(client, id):
        response = client.get(CHAPTERS_API, params={"id": id})
        result = singleton_or_none(response)
        return result["upload_warnings"], result["upload_errors"]
