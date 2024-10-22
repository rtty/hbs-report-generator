from datetime import date, timedelta

import pytest
import responses

from generator import accumulate_activities, produce_report
from hubstaff import (
    Hubstaff,
    DailyActivitiesResponse,
)

BASE_URL = 'https://localhost'

# Sample test data
API_TOKEN_RESPONSE = {'auth_token': 'sample_token'}
API_ORGANIZATIONS_RESPONSE = {
    'organizations': [{'id': 1, 'name': 'Organization 1'}, {'id': 2, 'name': 'Organization 2'}]
}
API_DAILY_ACTIVITIES_RESPONSE = {
    'daily_activities': [
        {
            'id': 1,
            'date': '2023-09-02',
            'user_id': 1,
            'project_id': 1,
            'task_id': None,
            'tracked': 3600,
            'manual': 0,
            'billable': 1,
        }
    ],
    'users': [
        {
            'id': 1,
            'name': 'User 1',
            'first_name': 'First',
            'last_name': 'Last',
            'email': 'user@example.com',
            'time_zone': 'UTC',
            'status': 'active',
        }
    ],
    'projects': [{'id': 1, 'name': 'Project 1', 'status': 'active', 'billable': True}],
}


@pytest.fixture
def patch_base_url_session():
    def all_matcher(request):
        return True, ''

    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.POST,
            f'{BASE_URL}/v454/account/signin',
            json=API_TOKEN_RESPONSE,
            status=200,
            match=[all_matcher],
        )
        yield rsps


@pytest.fixture
def hubstaff_client(patch_base_url_session):
    # initialize the Hubstaff client
    client = Hubstaff(
        base_url=f'{BASE_URL}',
        email='test@example.com',
        password='password',
        app_token='app_token',
    )
    return client


@responses.activate
def test_get_organizations(hubstaff_client, patch_base_url_session):
    # set up the mocked response
    responses.add(
        responses.GET,
        f'{BASE_URL}/v454/institution',
        json=API_ORGANIZATIONS_RESPONSE,
        status=200,
    )

    # call the get_organizations method
    response = hubstaff_client.get_organizations()

    # assert the response
    assert len(response.organizations) == 2
    assert response.organizations[0].id == 1
    assert response.organizations[0].name == 'Organization 1'
    assert response.organizations[1].id == 2
    assert response.organizations[1].name == 'Organization 2'

    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == f'{BASE_URL}/v454/institution?auth_token=sample_token'
    assert responses.calls[0].request.method == responses.GET


@responses.activate
def test_get_operations_by_day(hubstaff_client, patch_base_url_session):
    # Set up the mocked response
    responses.add(
        responses.GET,
        f'{BASE_URL}/v454/institution/1/operations/by_day',
        json=API_DAILY_ACTIVITIES_RESPONSE,
        status=200,
    )
    responses.add(
        responses.GET,
        f'{BASE_URL}/v454/institution/2/operations/by_day',
        json=API_DAILY_ACTIVITIES_RESPONSE,
        status=200,
    )

    # call the get_operations_by_day method
    response = hubstaff_client.get_operations_by_day(
        organization_id=1, date_start=date(2024, 9, 2), date_stop=date(2024, 9, 3)
    )

    # assert the response
    assert len(response.daily_activities) == 1
    assert response.daily_activities[0].id == 1
    assert response.daily_activities[0].date == '2023-09-02'

    assert len(response.users) == 1
    user = next(iter(response.users))
    assert user.id == 1
    assert user.name == 'User 1'

    assert len(response.projects) == 1
    project = next(iter(response.projects))
    assert project.id == 1
    assert project.name == 'Project 1'

    assert len(responses.calls) == 1
    assert (
        responses.calls[0].request.url
        == f'{BASE_URL}/v454/institution/1/operations/by_day?auth_token=sample_token&include=users%2Cprojects'
    )
    assert responses.calls[0].request.method == responses.GET


def test_process_report_data():
    sample_data = DailyActivitiesResponse.model_validate(API_DAILY_ACTIVITIES_RESPONSE)
    expected_report = {'Project 1': {'User 1': timedelta(seconds=3600)}}
    report = accumulate_activities(sample_data)
    assert report == expected_report


@responses.activate
def test_generate_report(hubstaff_client, patch_base_url_session):
    responses.add(
        responses.GET,
        f'{BASE_URL}/v454/institution',
        json=API_ORGANIZATIONS_RESPONSE,
        status=200,
    )
    responses.add(
        responses.GET,
        f'{BASE_URL}/v454/institution/1/operations/by_day',
        json=API_DAILY_ACTIVITIES_RESPONSE,
        status=200,
    )
    responses.add(
        responses.GET,
        f'{BASE_URL}/v454/institution/2/operations/by_day',
        json=API_DAILY_ACTIVITIES_RESPONSE,
        status=200,
    )

    html_output = produce_report(
        hubstaff_client, date_start=date(2024, 9, 2), date_end=date(2024, 9, 3)
    )
    assert 'Organization 1' in html_output
    assert 'Organization 2' in html_output
    assert 'Project 1' in html_output
    assert 'User 1' in html_output
    assert '2024-09-02' in html_output
