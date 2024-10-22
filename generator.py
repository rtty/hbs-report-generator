import logging
import sys
from argparse import ArgumentParser
from datetime import timedelta, date
from traceback import format_exc
from typing import Dict

from jinja2 import Environment, FileSystemLoader
from pydantic import ValidationError, Field
from pydantic_settings import BaseSettings

from hubstaff import Hubstaff, DailyActivitiesResponse


# set up logging configuration
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler = logging.FileHandler('hbs-report-generator.log')
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)


class Settings(BaseSettings):
    """Configuration class for environment variables."""

    api_url: str = Field(alias='HUBSTAFF_API_URL')
    api_email: str = Field(alias='HUBSTAFF_API_EMAIl')
    api_password: str = Field(alias='HUBSTAFF_API_PASSWORD')
    api_token: str = Field(alias='HUBSTAFF_API_APP_TOKEN')

    class Config:
        env_file = '.env'


def accumulate_activities(activities: DailyActivitiesResponse) -> Dict[str, Dict[str, timedelta]]:
    """Processes report data into a format suitable for the HTML template."""

    project_map = {project.id: project.name for project in activities.projects}
    user_map = {user.id: user.name for user in activities.users}
    # prepare activities cross table
    daily_activity_summary = {
        project: {user: timedelta(0) for user in sorted(user_map.values())}
        for project in sorted(project_map.values())
    }
    # summarize activities
    for activity in activities.daily_activities:
        project_name = project_map[activity.project_id]
        user_name = user_map[activity.user_id]
        daily_activity_summary[project_name][user_name] += timedelta(seconds=activity.tracked)

    return daily_activity_summary


def render_html_template(tracked_activities: dict, report_date: date) -> str:
    """Renders report from HTML template."""
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('report.html')
    context = {'report_date': report_date, 'tracked_activities': tracked_activities}
    return template.render(context)


def produce_report(hubstaff_service: Hubstaff, date_start: date, date_end: date) -> str:
    """Collects data from Hubstaff Api and generates report based on HTML template."""
    org_response = hubstaff_service.get_organizations()

    tracked_activities = {}
    for org in org_response.organizations:
        operations = hubstaff_service.get_operations_by_day(
            organization_id=org.id,
            date_start=date_start,
            date_stop=date_end,
        )
        tracked_activities[org.name] = accumulate_activities(operations)

    return render_html_template(tracked_activities, date_start)


def main() -> None:
    """Main function to execute the report generation process."""

    parser = ArgumentParser(description='Generate a Hubstaff report.')

    parser.add_argument(
        '--date_start',
        type=date.fromisoformat,
        default=date.today() - timedelta(days=1),
        help='Start date for the report (format: YYYY-MM-DD). Default is yesterday.',
    )
    parser.add_argument(
        '--date_end',
        type=date.fromisoformat,
        help='End date for the report (format: YYYY-MM-DD).',
    )
    args = parser.parse_args()

    try:
        settings = Settings()
        service = Hubstaff(
            settings.api_url, settings.api_email, settings.api_password, settings.api_token
        )
        html_report = produce_report(service, args.date_start, args.date_end or args.date_start)
        sys.stdout.write(html_report)
        logger.info('Generated report for %s', args.date_start)
    except ValidationError:
        logger.error('Unable to parse data: %s', format_exc())
        sys.exit(1)
    except Exception:  # noqa
        logger.error('Failed to retrieve data: %s', format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()
