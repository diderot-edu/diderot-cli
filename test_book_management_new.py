import pytest
from rest_framework import status

from models import MANAGE_BOOK_API_NEW

pytestmark = pytest.mark.django_db


def test_unauthorized_request(api_client, mk_chapter):
    # Given a chapter in a course
    chapter = mk_chapter("chapter", 1)

    # When a user that is not logged in tries to access the endpoint
    route_params = {"course_id": chapter.course.pk, "book_id": chapter.book.pk,
                    "part_id": chapter.part.id, "chapter_id": chapter.id, "action": "publish"}
    url = (MANAGE_BOOK_API_NEW + "parts/{part_id}/manage-chapters/{chapter_id}/{action}/").format(**route_params)
    response = api_client.post(url, {})

    # Then they will get a 401 unauthorized response
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_students_forbidden(api_client, mk_chapter, student):
    # Given an unreleased chapter
    chapter = mk_chapter("chapter", 1)
    assert not chapter.is_released

    # And a student in the course
    api_client.force_authenticate(student)

    # When they try to access the book management endpoint
    route_params = {"course_id": chapter.course.pk, "book_id": chapter.book.pk,
                    "part_id": chapter.part.id, "chapter_id": chapter.id, "action": "publish"}
    url = (MANAGE_BOOK_API_NEW + "parts/{part_id}/manage-chapters/{chapter_id}/{action}/").format(**route_params)
    response = api_client.post(url, {})

    # Then they will get a 403 forbidden response
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # And the chapter would not be released
    assert not chapter.is_released


def test_create_part(api_client, book, pi):
    # Given a book with no parts
    assert book.part_set.count() == 0

    # And an instructor in the course
    api_client.force_authenticate(pi)

    # When they try to create a new part in a book
    route_params = {"course_id": book.course_id, "book_id": book.id}
    url = (MANAGE_BOOK_API_NEW + "parts/").format(**route_params)
    data = {"title": "title", "label": "label", "rank": 1}
    response = api_client.post(url, data)

    # Then the will get a success response
    assert response.status_code == status.HTTP_201_CREATED

    # And the part will have been created
    assert book.part_set.count() == 1
    assert book.part_set.first().title == "title"


def test_create_chapter(api_client, part, pi):
    # Given a book part with no chapters
    assert part.chapter_set.count() == 0

    # And an instructor in the course
    api_client.force_authenticate(pi)

    # When they try to create a new chapter
    route_params = {"course_id": part.book.course_id, "book_id": part.book_id, "part_id": part.id}
    url = (MANAGE_BOOK_API_NEW + "parts/{part_id}/manage-chapters/").format(**route_params)
    data = {"title": "title", "label": "label", "rank": 1}
    response = api_client.post(url, data)

    # Then the will get a success response
    assert response.status_code == status.HTTP_201_CREATED

    # And the chapter will have been created
    assert part.chapter_set.count() == 1
    assert part.chapter_set.first().title == "title"


def test_release_chapter(api_client, mk_chapter, pi):
    # Given an unreleased chapter
    chapter = mk_chapter("chapter", 1)
    assert not chapter.is_released

    # And an instructor in the course
    api_client.force_authenticate(pi)

    # When an instructor tries to release the chapter
    route_params = {"course_id": chapter.course.pk, "book_id": chapter.book.pk,
                    "part_id": chapter.part.id, "chapter_id": chapter.id, "action": "publish"}
    url = (MANAGE_BOOK_API_NEW + "parts/{part_id}/manage-chapters/{chapter_id}/{action}/").format(**route_params)
    response = api_client.post(url, {})

    # Then the will get a success response
    assert response.status_code == status.HTTP_200_OK

    # And the chapter will have been released
    chapter.refresh_from_db()
    assert chapter.is_released


def test_unrelease_chapter(api_client, mk_chapter, pi):
    # Given a released chapter
    chapter = mk_chapter("chapter", 1)
    chapter.is_released = True
    chapter.save()

    # And an instructor in the course
    api_client.force_authenticate(pi)

    # When they try to unrelease the chapter
    route_params = {"course_id": chapter.course.pk, "book_id": chapter.book.pk,
                    "part_id": chapter.part.id, "chapter_id": chapter.id, "action": "retract"}
    url = (MANAGE_BOOK_API_NEW + "parts/{part_id}/manage-chapters/{chapter_id}/{action}/").format(**route_params)
    response = api_client.post(url, {})

    # Then the will get a success response
    assert response.status_code == status.HTTP_200_OK

    # And the chapter will have been retracted
    chapter.refresh_from_db()
    assert not chapter.is_released


@pytest.mark.django_db(transaction=True)
def test_upload_chapter(api_client, join_threads, mk_chapter, pi):
    # Given an existing chapter with no content
    chapter = mk_chapter("chapter", 1)
    assert not chapter.html
    assert not chapter.source_xml

    # And an instructor in the course
    api_client.force_authenticate(pi)

    # When they try to upload new contents for the chapter
    route_params = {"course_id": chapter.course.pk, "book_id": chapter.book.pk,
                    "part_id": chapter.part.id, "chapter_id": chapter.id, "action": "content_upload"}
    url = (MANAGE_BOOK_API_NEW + "parts/{part_id}/manage-chapters/{chapter_id}/{action}/").format(**route_params)
    data = {"input_file_xml": open("test-data/books/part-graph-contraction/introduction.xml", "r")}
    response = api_client.post(url, data, format="multipart")

    # Then the will get a success response
    assert response.status_code == status.HTTP_200_OK

    # And the chapter contents will have been uploaded
    join_threads()
    chapter.refresh_from_db(fields=['html', 'source_xml'])  # Deferred fields are not refreshed by default
    assert chapter.html
    assert chapter.source_xml
