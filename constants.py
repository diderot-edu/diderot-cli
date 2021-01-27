# URL constants for API access.
COURSE_API = "/frontend-api/courses/courses/available/"
LAB_API = "/frontend-api/courses/{}/codelabs/"
BOOK_API = "/frontend-api/books/cli/"
PARTS_API = "/frontend-api/parts/cli/"
CHAPTERS_API = "/frontend-api/chapters/cli/"
MANAGE_BOOK_API = "/frontend-api/courses/{course_id}/books/{book_id}/"
SUBMIT_ASSIGNMENT_API = "/frontend-api/courses/{}/codelabs/{}/submissions/create_and_submit/"
UPLOAD_FILES_API = "/frontend-api/courses/{}/codelabs/{}/"
LOGIN_URL = "/frontend-api/users/login/"

DEFAULT_CRED_LOCATIONS = ["~/private/.diderot/credentials", "~/.diderot/credentials"]

ADDR = "127.0.0.1"
PORT = 8080
SERVURL = "http://{}:{}".format(ADDR, PORT)
