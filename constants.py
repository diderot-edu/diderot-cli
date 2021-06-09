# URL constants for API access.
COURSE_API = "/api/courses/courses/"
LAB_API = "/api/courses/{}/codelabs/"
BOOK_API = "/api/books/cli/"
PARTS_API = "/api/parts/cli/"
CHAPTERS_API = "/api/chapters/cli/"
MANAGE_BOOK_LIST_API = "/api/courses/{course_id}/manage-books/"
MANAGE_BOOK_API = "/api/courses/{course_id}/books/{book_id}/"
MANAGE_CHAPTER_WITH_ACTION_API = MANAGE_BOOK_API + "manage-chapters/{chapter_id}/{action}/"
SUBMIT_ASSIGNMENT_API = "/api/courses/{}/codelabs/{}/submissions/create_and_submit/"
UPLOAD_FILES_API = "/api/courses/{}/codelabs/{}/"
LOGIN_URL = "/api/users/login/"

DEFAULT_CRED_LOCATIONS = ["~/private/.diderot/credentials", "~/.diderot/credentials"]

ADDR = "127.0.0.1"
PORT = 8080
SERVURL = "http://{}:{}".format(ADDR, PORT)
