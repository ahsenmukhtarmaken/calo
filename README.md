#CALO Logs Processor

#Docker Build
`docker build -t calodemo .`

#Uncompress logs and place in logs_extracted folder from logs folder
`docker run -it calodemo logsProcessor.py`

#Generates over drawn reports
`docker run -it calodemo generate_overdrawn_reports.py`

#Generate other anomoly errors reports
`docker run -it calodemo generate_errors_report.py`
