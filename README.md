#CALO Logs Processor

Code Running Guide:
1. Install docker on your machine.
2. once installed run docker and after that open a command line/shell
3. run below command for Docker Build:
`docker build -t calodemo .`

4. run below command to Uncompress logs and place in logs_extracted folder from logs folder
`docker run -it calodemo python logsProcessor.py`

5. run below command to Generates over drawn reports:
`docker run -it calodemo python generate_overdrawn_reports.py`

6. run below command to generate other anomoly errors reports:
`docker run -it calodemo python generate_errors_report.py`

7. In CALO/logs folder the provided logs have been placed
8. In CALO/logs_extracted folder the uncompressed log files are now placed.
9. In CALO/reports all the reports have been generated.
    (1) First  report is overdrawn_transactions_report.csv which has all the overdrawn transactions.
    (2) Second report is overdrawn_daily.csv which has date level information available.
    (3) Third  report is overdrawn_weekly.csv which has week level information available.
    (4) Fourth report is overdrawb_monthly.csv which has month level information available.
    (5) Fifth  report is overdrawb_yearly.csv which has year level information available.
    (6) Sixth  report is to identify the bonus part listing all anomolies like Null balance or balance not being in sync with subscription or run time errors at POS.

10. Once reports are generated run below command for automated testing:
`docker run -it calodemo pytest -v`