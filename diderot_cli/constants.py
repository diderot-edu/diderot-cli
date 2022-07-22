# URL constants for API access.
COURSE_API = "/api/courses/courses/"
LAB_API = "/api/courses/{}/codelabs/"
BOOK_API = "/api/books/cli/"
PARTS_API = "/api/parts/cli/"
CHAPTERS_API = "/api/chapters/cli/"
MANAGE_BOOK_LIST_API = "/api/courses/{course_id}/manage-books/"
MANAGE_BOOK_API = "/api/courses/{course_id}/books/{book_id}/"
MANAGE_CHAPTER_API = MANAGE_BOOK_API + "manage-chapters/{chapter_id}/"
MANAGE_CHAPTER_WITH_ACTION_API = MANAGE_BOOK_API + "manage-chapters/{chapter_id}/{action}/"
SUBMIT_ASSIGNMENT_API = "/api/courses/{}/codelabs/{}/submissions/create_and_submit/"
UPLOAD_FILES_API = "/api/courses/{}/codelabs/{}/"
FILE_URLS_API = "api/courses/{}/codelabs/{}/attached_file_urls/"
LOGIN_URL = "/api/users/login/"

DEFAULT_CRED_LOCATIONS = ["~/private/.diderot/credentials", "~/.diderot/credentials"]

DEFAULT_DIDEROT_URL = "https://api.diderot.one"

# OPTIONS
# Click converts dashes in options to underscores for
# access (get) operations.
# Hence we define both here
ATTACH = "attach"
ATTACH_GET = "attach"
PART_LABEL = "part-label"
PART_LABEL_GET = "part_label"
PART_NUMBER = "part-number"
PART_NUMBER_GET = "part_number"
CHAPTER_LABEL = "chapter-label"
CHAPTER_LABEL_GET = "chapter_label"
CHAPTER_NUMBER = "chapter-number"
CHAPTER_NUMBER_GET = "chapter_number"
PDF = "pdf"
PDF_GET = "pdf"
PUBLISH_DATE = "publish-date"
PUBLISH_DATE_GET = "publish_date"
PUBLISH_ON_WEEK = "publish-on-week"
PUBLISH_ON_WEEK_GET = "publish_on_week"
SCHEDULE_DATE = "schedule-date"
SCHEDULE_ON_WEEK = "schedule-on-week"
SLEEP_TIME = "sleep-time"
SLEEP_TIME_GET = "sleep_time"
VIDEO_URL = "video-url"
VIDEO_URL_GET = "video_url"
XML = "xml"
XML_GET = "xml"
XML_PDF = "xml-pdf"
XML_PDF_GET = "xml_pdf"




# For tests
ADDR = "127.0.0.1"
PORT = 8080
SERVURL = "http://{}:{}".format(ADDR, PORT)

