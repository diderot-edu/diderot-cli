default: test

admin_release:
	tar -cvf admin_release.tar standalone.py api_calls.py diderot_admin

student_release:
	tar -cvf student_release.tar standalone.py api_calls.py diderot_student

test:
	./test.py -v

clean:
	rm -f admin_release.tar student_release.tar
