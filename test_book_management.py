import pytest
from rest_framework import status

from models import MANAGE_BOOK_API

pytestmark = pytest.mark.django_db


def test_unauthorized_request(client_anon, chapter):
    # Given a chapter in a course

    # When a user that is not logged in tries to access the endpoint
    url = MANAGE_BOOK_API.format(chapter.get_course().pk, chapter.get_book().pk)
    data = {"kind": "release", "chapter_pk": chapter.pk}
    response = client_anon.post(url, data)

    # Then they will get a redirect response to the login page
    assert response.status_code == status.HTTP_302_FOUND
    assert "/login/login/" in response.url


def test_students_forbidden(client_student, chapter):
    # Given a chapter in a course

    # When a student tries to access the book management endpoint
    url = MANAGE_BOOK_API.format(chapter.get_course().pk, chapter.get_book().pk)
    data = {"kind": "release", "chapter_pk": chapter.pk}
    response = client_student.post(url, data)

    # Then they will be redirected to the home page
    assert response.status_code == status.HTTP_302_FOUND
    assert "/" in response.url

    # And the chapter will remain unchanged
    assert not chapter.is_released


def test_create_part(client_pi, book):
    # Given a book with no parts
    assert book.part_set.count() == 0

    # When an instructor tries to create a new part
    url = MANAGE_BOOK_API.format(book.course_id, book.id)
    data = {"kind": "create part", "rank": 1, "title": "title", "label": "label"}
    response = client_pi.post(url, data)

    # Then the will get a success response (which is a redirect to the book page in this case)
    assert response.status_code == status.HTTP_302_FOUND
    assert response.url == url

    # And the part will have been created
    assert book.part_set.count() == 1
    assert book.part_set.first().title == "title"


def test_create_chapter(client_pi, part):
    # Given a book part with no chapters
    assert part.chapter_set.count() == 0

    # When an instructor tries to create a new chapter
    url = MANAGE_BOOK_API.format(part.book.course_id, part.book_id)
    data = {"kind": "create chapter", "part_pk": part.pk, "rank": 1, "title": "title", "label": "label"}
    response = client_pi.post(url, data)

    # Then the will get a success response (which is a redirect to the book page in this case)
    assert response.status_code == status.HTTP_302_FOUND
    assert response.url == url

    # And the chapter will have been created
    assert part.chapter_set.count() == 1
    assert part.chapter_set.first().title == "title"


def test_release_chapter(client_pi, chapter):
    # Given an instructor in the course

    # And an unreleased chapter
    assert not chapter.is_released

    # When an instructor tries to release the chapter
    url = MANAGE_BOOK_API.format(chapter.get_course().pk, chapter.get_book().pk)
    data = {"kind": "release", "chapter_pk": chapter.pk}
    response = client_pi.post(url, data)

    # Then the will get a success response (which is a redirect to the book page in this case)
    assert response.status_code == status.HTTP_302_FOUND
    assert response.url == url

    # And the chapter will have been released
    chapter.refresh_from_db()
    assert chapter.is_released


def test_unrelease_chapter(client_pi, chapter):
    # Given an instructor in the course

    # And a released chapter
    chapter.is_released = True
    chapter.save()

    # When an instructor tries to release the chapter
    url = MANAGE_BOOK_API.format(chapter.get_course().pk, chapter.get_book().pk)
    data = {"kind": "unrelease", "chapter_pk": chapter.pk}
    response = client_pi.post(url, data)

    # Then the will get a success response (which is a redirect to the book page in this case)
    assert response.status_code == status.HTTP_302_FOUND
    assert response.url == url

    # And the chapter will have been released
    chapter.refresh_from_db()
    assert not chapter.is_released


@pytest.mark.django_db(transaction=True)
def test_upload_chapter(client_pi, chapter, join_threads):
    # Given a created chapter with no content
    assert not chapter.html
    assert not chapter.source_xml

    # When an instructor tries to upload new contents for the chapter
    url = MANAGE_BOOK_API.format(chapter.course_id, chapter.book_id)
    data = {"kind": "upload content",
            "chapter_pk": chapter.pk,
            "input_file_xml": open("test-data/books/part-graph-contraction/introduction.xml", "r")
            }
    response = client_pi.post(url, data)

    # Then the will get a success response (which is a redirect to the book page in this case)
    assert response.status_code == status.HTTP_302_FOUND
    assert response.url == url

    # And the chapter contents will have been uploaded
    join_threads()
    chapter.refresh_from_db(fields=['html', 'source_xml'])  # Deferred fields are not refreshed by default
    assert chapter.html
    assert chapter.source_xml
