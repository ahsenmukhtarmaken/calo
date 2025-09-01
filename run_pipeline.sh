docker build -t calodemo .
docker run -it calodemo python logsProcessor.py
docker run -it calodemo python generate_overdrawn_reports.py
docker run -it calodemo python generate_errors_report.py
docker run -it calodemo pytest -v