from getpass import getpass
from werkzeug.security import generate_password_hash

password = getpass("New admin password: ")
confirm = getpass("Confirm password: ")
if password != confirm:
    raise SystemExit("Passwords do not match")
if len(password) < 10:
    raise SystemExit("Use at least 10 characters")
print(generate_password_hash(password))
