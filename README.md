# Hubstaff Report Generator

This guide provides instructions for deploying the Hubstaff Report Generator.

## Prerequisites

Before you begin, ensure that you have the following installed:

1. **Python 3.11**
2. **[Docker](https://www.docker.com/)**

## Configuration

The configuration settings are defined in the `.env` file, and you can override them by setting the corresponding environment variables. Below is a comprehensive list of the available variables:

| Variable                 | Description                                    |
|--------------------------|------------------------------------------------|
| `HUBSTAFF_API_URL`       | The base URL for the Hubstaff REST API.        |
| `HUBSTAFF_API_EMAIL`     | The email address of the Hubstaff user.        |
| `HUBSTAFF_API_PASSWORD`  | The password for the Hubstaff user.            |
| `HUBSTAFF_API_APP_TOKEN` | The authentication token for the Hubstaff API. |

## Installation

To install the necessary Python dependencies, follow these steps:

```bash
pip install poetry
poetry install
```

## Testing 

You can run the tests using the following command:

```bash
poetry run pytest
```

## Running the Report Generator

To view the available options for generating a report, run generator.py with the -h argument:

```bash
usage: generator.py [-h] [--date_start DATE_START] [--date_end DATE_END]

Generate a Hubstaff report.

options:
  -h, --help            show this help message and exit
  --date_start DATE_START
                        Start date for the report (format: YYYY-MM-DD). Default is yesterday.
  --date_end DATE_END   End date for the report (format: YYYY-MM-DD).
```

To generate a report for yesterday's date, simply run:

```bash
python generator.py
```
or redirect output to file:
```bash
./generator-local.sh
```
The report file will be saved in the `reports` folder. Log file is `hbs-report-generator.log`.

## Scheduling with cron

To automate the report generation, you can add the following line to your crontab:

```bash
crontab -e
0 1 * * * /path/to/hbs-report-generator/generator-local.sh
```
This schedules the report generation to run daily at 1 AM.

## Running with Docker

You can also run the report generator using Docker. Use the following command to build and run the Docker container:

```bash
./generator-docker.sh
```

```bash
cromtab -e
0 1 * * * /path/to/hbs-report-generator/generator-docker.sh
```

## Sending the report via email using sendmail

After generating the report, you can send it via email using the `sendmail` command. Below is an example of how to do this.

### Compose the email and attach the report:

```bash
SUBJECT="Hubstaff Daily Report - $(date -d 'yesterday' '+%Y-%m-%d')"
EMAIL="recipient@example.com"
REPORT="reports/daily_report_$(date -d 'yesterday' '+%Y-%d-%m').html"

{
    echo "Subject: $SUBJECT"
    echo "To: $EMAIL"
    echo "Content-Type: text/html"
    echo
    cat "$REPORT"
} | sendmail -t
```
### Automate email sending:

You can add this script to a cron job to automatically send the report every day after it is generated. For example, if the report is generated at 1 AM:
```bash
crontab -e
0 2 * * * /path/to/send_report.sh
```
This cron job will send the report at 2 AM daily.
