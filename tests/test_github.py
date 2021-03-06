# -*- coding: utf-8 -*-
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""Tests bot communication with Github"""
import os
import pytest

from release_bot.configuration import configuration
from release_bot.github import Github
from github_utils import GithubUtils, RELEASE_CONF


@pytest.mark.skipif(not GithubUtils.github_api_status(), reason="Github api is down")
@pytest.mark.skipif(not os.environ.get('GITHUB_TOKEN') and not os.environ.get('GITHUB_USER'),
                    reason="missing GITHUB_TOKEN and GITHUB_USER variables")
class TestGithub:
    """Tests bot communication with Github"""
    github_token = os.environ.get('GITHUB_TOKEN')
    github_user = os.environ.get('GITHUB_USER')
    headers = {'Authorization': f'token {github_token}'}

    def setup_method(self):
        """ setup any state tied to the execution of the given method in a
        class.  setup_method is invoked for every test method of a class.
        """
        configuration.set_logging(level=10)
        configuration.debug = True

        self.g_utils = GithubUtils(self.github_token, self.github_user)

        self.g_utils.create_repo()
        self.g_utils.setup_repo()

        # set conf
        configuration.repository_name = self.g_utils.repo
        configuration.repository_owner = self.github_user
        configuration.github_token = self.github_token
        configuration.github_username = self.github_user
        configuration.refresh_interval = 1

        self.github = Github(configuration)

    def teardown_method(self):
        """ teardown any state that was previously setup with a setup_method
        call.
        """
        if self.g_utils.repo:
            self.g_utils.delete_repo()
        self.g_utils.repo = None

    @pytest.fixture()
    def open_issue(self):
        """Opens issue in a repository"""
        return self.g_utils.open_issue()

    @pytest.fixture()
    def open_issue_graphql(self):
        """Opens issue and returns it's GraphQL id"""
        number = self.g_utils.open_issue()
        query = f"issue(number: {number}) {{id}}"
        response = self.github.query_repository(query).json()
        self.github.detect_api_errors(response)

        return number, response['data']['repository']['issue']['id']

    def test_get_configuration(self):
        """Tests fetching release-conf from Github"""
        assert self.github.get_configuration() == RELEASE_CONF

    def test_close_issue(self, open_issue):
        """Tests closing issue"""
        assert self.github.close_issue(open_issue)

    def test_latest_rls_not_existing(self):
        """Tests version number when there is no latest relase"""
        assert not self.github.latest_release()

    def test_branch_exists_true(self):
        """Tests if branch exists"""
        assert self.github.branch_exists('master')

    def test_branch_exists_false(self):
        """Tests if branch doesn't exist"""
        assert not self.github.branch_exists('not-master')

    def test_add_comment(self, open_issue_graphql):
        """Tests adding comment on issue"""
        number, graphql_id = open_issue_graphql
        comments_count = self.g_utils.count_comments(number)
        self.github.comment = "Test comment"
        self.github.add_comment(graphql_id)
        assert self.g_utils.count_comments(number) == comments_count + 1
