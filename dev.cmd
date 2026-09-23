@echo off
rem DEV ONLY. Runs the whole Walkthru stack (API, web, fixtures, extension build). Remove before production.
"%~dp0apps\api\.venv\Scripts\python.exe" "%~dp0dev.py" %*
