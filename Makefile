default: test

admin_release:
	tar -cvf admin_release.tar standalone.py api_calls.py diderot_admin

student_release:
	tar -cvf student_release.tar standalone.py api_calls.py diderot_student

test:
	./test.py -v

coverage:
	coverage run --source='.' ./test.py
	coverage report

clean:
	rm -f admin_release.tar student_release.tar
