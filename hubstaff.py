import logging
from datetime import date
from typing import List, Dict, Optional, Set

import pydantic
import requests
from pydantic import BaseModel
from requests_toolbelt import MultipartEncoder, sessions
from tenacity import (
    retry,
    stop_after_attempt,
    wait_fixed,
    retry_if_not_exception_type,
)

logger = logging.getLogger(__name__)


# Response models
class AuthTokenResponse(BaseModel):
    """Model for the response containing the authentication token."""

    auth_token: str


class PageableModel(BaseModel):
    """Pageable details model."""

    next_page_start_id: int


class PageableResponse(BaseModel):
    """Base pageable model for the response."""

    pagination: Optional[PageableModel] = None


class OrganizationModel(BaseModel):
    """Model for the response containing organization details."""

    id: int
    name: str


class OrganizationsResponse(PageableResponse):
    """Model for the response containing organization details."""

    organizations: List[OrganizationModel]


class User(BaseModel, frozen=True):
    """Model for user details."""

    id: int
    name: str
    first_name: str
    last_name: str
    email: str
    time_zone: str
    status: str


class Project(BaseModel, frozen=True):
    """Model for project details."""

    id: int
    name: str
    status: str
    billable: bool


class DailyActivity(BaseModel):
    """Model for daily activity details."""

    id: int
    date: str
    user_id: int
    project_id: int
    task_id: Optional[int]
    tracked: int
    manual: int
    billable: int


class DailyActivitiesResponse(PageableResponse):
    """Model for the report response containing activities, users, and projects."""

    daily_activities: List[DailyActivity]
    users: Set[User]
    projects: Set[Project]


# Api wrapper
class Hubstaff:
    """Hubstaff api client."""

    DEFAULT_TIMEOUT = 10

    def __init__(self, base_url: str, email: str, password: str, app_token: str):
        self.http = sessions.BaseUrlSession(base_url=base_url)
        self.http.headers['Accept'] = 'application/json'
        self.http.headers['AppToken'] = app_token
        self.http.hooks['response'] = lambda response, *args, **kwargs: response.raise_for_status()

        # authenticate and store the token
        self.http.params = {'auth_token': self.authenticate(email, password).auth_token}

    def authenticate(self, email: str, password: str) -> AuthTokenResponse:
        """Authenticates user and return the authentication token."""

        api_path = '/v454/account/signin'
        payload = MultipartEncoder({'email': email, 'password': password})
        response = self.__send_request(
            method='post',
            path=api_path,
            data=payload,
            headers={'Content-Type': payload.content_type},
            response_type=AuthTokenResponse,
        )
        return response

    def get_organizations(self) -> OrganizationsResponse:
        """Retrieves organizations using the authentication token."""

        api_path = '/v454/institution'
        result = OrganizationsResponse(organizations=[])
        params = {}

        has_next_page = True
        while has_next_page:
            response = self.__send_request(
                method='get', path=api_path, params=params, response_type=OrganizationsResponse
            )

            result.organizations.extend(response.organizations)

            if has_next_page := response.pagination is not None:
                params.update({'page_start_id': response.pagination.next_page_start_id})

        return result

    def get_operations_by_day(
        self, organization_id: int, date_start: date, date_stop: date
    ) -> DailyActivitiesResponse:
        """
        Fetches daily activities data for the specified date range and organization.
        Handles pagination to fetch all pages of data.
        """
        api_path = f'/v454/institution/{organization_id}/operations/by_day'

        result = DailyActivitiesResponse(daily_activities=[], users=set(), projects=set())
        params = {'include': 'users,projects'}

        has_next_page = True
        while has_next_page:
            response = self.__send_request(
                method='get',
                path=api_path,
                params=params,
                headers={
                    'DateStart': date_start.strftime('%Y-%m-%d'),
                    'DateStop': date_stop.strftime('%Y-%m-%d'),
                },
                response_type=DailyActivitiesResponse,
            )
            result.daily_activities.extend(response.daily_activities)
            result.users.update(response.users)
            result.projects.update(response.projects)

            if has_next_page := response.pagination is not None:
                params.update({'page_start_id': response.pagination.next_page_start_id})

        return result

    @retry(
        retry=retry_if_not_exception_type(pydantic.ValidationError),
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        reraise=True,
    )
    def __send_request(
        self,
        method: str,
        path: str,
        params: Dict[str, str] | None = None,
        headers: Dict[str, str] | None = None,
        data: Dict[str, str] | MultipartEncoder | None = None,
        response_type: BaseModel | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> requests.Response | BaseModel:
        """Makes an HTTP request with specified method, path, parameters and headers."""

        logger.info('%s path=%s params=%s headers=%s', method.upper(), path, params, headers)
        response = self.http.request(
            method=method, url=path, params=params, headers=headers, data=data, timeout=timeout
        )
        return response if response_type is None else response_type.model_validate(response.json())
