from cli_utils import APIError, BookNotFoundAPIError, singleton_or_none
from constants import (
    COURSE_API,
    LAB_API,
    BOOK_API,
    PARTS_API,
    CHAPTERS_API,
    MANAGE_BOOK_API,
    MANAGE_BOOK_LIST_API,
)


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
            if len(response.json()) == 0:
                raise BookNotFoundAPIError("Input book not found.")
            raise APIError("Input book not found.")
        self.pk = result["id"]

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

    @staticmethod
    def create(course, title, label):
        data = {"title": title, "label": label}

        route_params = {"course_id": course.pk}
        course.client.post(MANAGE_BOOK_LIST_API.format(**route_params), data=data)


class Part:
    def __init__(self, course, book, number):
        self.course = course
        self.book = book
        self.client = course.client
        self.pk = None
        self._verify(number)

    def _verify(self, number):
        # If we have a booklet, then don't look at number.
        params = {"book__id": self.book.pk, "rank": number}
        response = self.client.get(PARTS_API, params=params)
        result = singleton_or_none(response)
        if result is None:
            raise APIError("Input part not found.")
        self.pk = result["id"]

    @staticmethod
    def create(course, book, title, number, label):
        data = {"title": title, "rank": number}
        if label is not None:
            data["label"] = label

        route_params = {"course_id": course.pk, "book_id": book.pk}
        course.client.post((MANAGE_BOOK_API + "parts/").format(**route_params), data=data)

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
    def __init__(self, course, book, number, label, publish_date=None, due_date=None):
        self.course = course
        self.book = book
        self.client = course.client
        self.pk = None
        self.number = None
        self.label = None
        self.part_id = None
        self.publish_date = publish_date
        self.due_date = due_date
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
        self.part_id = result["part"]

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
    def create(course, book, part, number, title, label, date_release=None, publish_on_week=None):
        data = {"rank": number}
        if title is not None:
            data["title"] = title
        if label is not None:
            data["label"] = label
        if date_release is not None:
            data["date_release"] = date_release
        if publish_on_week is not None:
            data["publish_on_week"] = publish_on_week

        data["part"] = part.pk

        route_params = {"course_id": course.pk, "book_id": book.pk}
        course.client.post((MANAGE_BOOK_API + "manage-chapters/").format(**route_params), data=data)

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
