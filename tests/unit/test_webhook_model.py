#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Tests for webhooks.model.WebHookIssue methods."""

from dataclasses import asdict
import json
import logging
from unittest.mock import patch

import pytest
from requests.exceptions import HTTPError

import webcompat
from tests.unit.test_webhook import event_data
from webcompat.webhooks.model import WebHookIssue

AUTOCLOSED_MILESTONE_ID = webcompat.app.config['AUTOCLOSED_MILESTONE_ID']

# Some expected responses as tuples
accepted = ('Moderated issue accepted', 200, {'Content-Type': 'text/plain'})
rejected = ('Moderated issue rejected', 200, {'Content-Type': 'text/plain'})
incomplete = ('Moderated issue closed as incomplete',
              200, {'Content-Type': 'text/plain'})
invalid = ('Moderated issue closed as invalid',
           200, {'Content-Type': 'text/plain'})
autoclosed = ('Issue closed as invalid by ml bot',
              200, {'Content-Type': 'text/plain'})
boring = ('Not an interesting hook', 403, {'Content-Type': 'text/plain'})
gracias = ('gracias, amigo.', 200, {'Content-Type': 'text/plain'})
wrong_repo = ('Wrong repository', 403, {'Content-Type': 'text/plain'})
oops = ('oops', 400, {'Content-Type': 'text/plain'})
comment_added = ('public url added and issue classified', 200, {'Content-Type': 'text/plain'})  # noqa
outreach_comment_added = ('outreach generator url added', 200, {'Content-Type': 'text/plain'})  # noqa

issue_info1 = {
    'action': 'opened', 'state': 'open',
    'milestoned_with': '', 'labeled_with': '',
    'milestone': '', 'body': '<!-- @browser: Firefox 55.0 -->\n<!-- @ua_header: Mozilla/5.0 (X11; Linux x86_64; rv:55.0) Gecko/20100101 Firefox/55.0 -->\n<!-- @reported_with: web -->\n<!-- @public_url: https://github.com/webcompat/webcompat-tests/issues/1  -->\n\n**URL**: https://www.netflix.com/',   # noqa
    'domain': 'www.netflix.com', 'number': 600,
    'original_labels': ['action-needsmoderation'],
    'public_url': 'https://github.com/webcompat/webcompat-tests/issues/1',
    'repository_url': 'https://api.github.com/repos/webcompat/webcompat-tests-private',  # noqa
    'title': 'www.netflix.com - test valid event',
    'host_reported_from': '',
    'html_url': 'https://github.com/webcompat/webcompat-tests-private/issues/600'       # noqa
}

issue_info2 = {
    'action': 'milestoned', 'state': 'open',
    'milestoned_with': 'accepted', 'labeled_with': '',
    'milestone': 'accepted', 'body': '<!-- @browser: Firefox 55.0 -->\n<!-- @ua_header: Mozilla/5.0 (X11; Linux x86_64; rv:55.0) Gecko/20100101 Firefox/55.0 -->\n<!-- @reported_with: web -->\n<!-- @public_url: https://github.com/webcompat/webcompat-tests/issues/1  -->\n\n**URL**: https://www.netflix.com/',  # noqa
    'domain': 'www.netflix.com', 'number': 600,
    'original_labels': ['action-needsmoderation'],
    'public_url': 'https://github.com/webcompat/webcompat-tests/issues/1',
    'repository_url': 'https://api.github.com/repos/webcompat/webcompat-tests-private',  # noqa
    'title': 'www.netflix.com - test private issue accepted',
    'host_reported_from': '',
    'html_url': 'https://github.com/webcompat/webcompat-tests-private/issues/600'       # noqa
}


def test_model_instance():
    """Test initializing a WebHookIssue model instance:

    1. from a private new issue
    2. from a milestoned issue
    """
    json_event, signature = event_data('private_issue_opened.json')
    payload = json.loads(json_event)
    issue = WebHookIssue.from_dict(payload)
    expected = issue_info1
    assert expected == asdict(issue)

    json_event, signature = event_data('private_milestone_accepted.json')
    payload = json.loads(json_event)
    issue = WebHookIssue.from_dict(payload)
    expected = issue_info2
    assert expected == asdict(issue)


@patch('webcompat.webhooks.model.make_request')
def test_close_private_issue(mock_mr):
    """Test issue state and API request that is sent to GitHub."""
    json_event, signature = event_data('private_issue_opened.json')
    payload = json.loads(json_event)
    issue = WebHookIssue.from_dict(payload)
    issue.close_private_issue()
    method, uri, data = mock_mr.call_args[0]
    # make sure our issue state is what we expect
    assert issue.state == 'closed'
    # make sure we sent a patch with the right data to GitHub
    assert method == 'patch'
    assert 'state' in data


@patch('webcompat.webhooks.model.make_request')
def test_close_private_issue_fails(mock_mr):
    """Test issue state after a simulated GitHub failure."""
    mock_mr.side_effect = HTTPError()
    mock_mr.status_code = 400
    json_event, signature = event_data('private_issue_opened.json')
    payload = json.loads(json_event)
    issue = WebHookIssue.from_dict(payload)
    with pytest.raises(HTTPError):
        issue.close_private_issue()
    assert issue.state == 'open'


@patch('webcompat.webhooks.model.make_request')
def test_comment_public_uri(mock_mr):
    """Test issue state and API request that is sent to GitHub."""
    json_event, signature = event_data('private_issue_opened.json')
    payload = json.loads(json_event)
    issue = WebHookIssue.from_dict(payload)
    issue.comment_public_uri()
    method, uri, data = mock_mr.call_args[0]
    # make sure we sent a post with the right data to GitHub
    assert method == 'post'
    assert 'body' in data
    assert str(issue.number) in uri


@patch('webcompat.webhooks.model.make_request')
def test_comment_closed_reason(mock_mr):
    """Test comment API request that is sent to GitHub."""
    json_event, signature = event_data('private_issue_opened.json')
    payload = json.loads(json_event)
    issue = WebHookIssue.from_dict(payload)
    reasons = ['invalid', 'incomplete']
    for reason in reasons:
        issue.comment_closed_reason(reason)
    method, uri, data = mock_mr.call_args[0]
    # make sure we sent a post with the right data to GitHub
    assert method == 'post'
    assert reason in data['body'].lower()
    assert str(issue.get_public_issue_number()) in uri
    with pytest.raises(ValueError):
        issue.comment_closed_reason('boring garbage')


@patch('webcompat.webhooks.model.make_request')
def test_moderate_public_issue(mock_mr):
    """Test issue state and API request that is sent to GitHub."""
    json_event, signature = event_data('private_issue_opened.json')
    payload = json.loads(json_event)
    issue = WebHookIssue.from_dict(payload)
    issue.moderate_private_issue()
    method, uri, data = mock_mr.call_args[0]
    # make sure we sent a patch with the right data to GitHub
    assert method == 'patch'
    assert 'title' in data
    assert 'body' in data
    assert 'labels' in data
    assert issue.get_public_issue_number() in uri


@patch('webcompat.webhooks.model.make_request')
def test_closing_public_issues(mock_mr):
    """Test issue state and API request that is sent to GitHub."""
    json_event, signature = event_data('private_issue_opened.json')
    payload = json.loads(json_event)
    issue = WebHookIssue.from_dict(payload)
    reasons = ['incomplete', 'invalid', 'rejected']
    for reason in reasons:
        issue.close_public_issue(reason=reason)
        method, uri, data = mock_mr.call_args[0]
        # make sure we sent a patch with the right data to GitHub
        assert method == 'patch'
        assert type(data) == dict
        assert issue.get_public_issue_number() in uri


@patch('webcompat.webhooks.model.make_request')
def test_autoclose_public_issue(mock_mr):
    """Test API request that is sent to GitHub for auto closed issue."""
    json_event, signature = event_data('private_milestone_ml_autoclosed.json')
    payload = json.loads(json_event)
    issue = WebHookIssue.from_dict(payload)
    issue.close_public_issue(reason='autoclosed')
    method, uri, data = mock_mr.call_args[0]
    # make sure we sent a patch with the right data to GitHub
    assert method == 'patch'
    assert type(data) == dict
    assert issue.get_public_issue_number() in uri
    assert issue.html_url in data['body']


def test_prepare_public_comment():
    """Test we prepare the right comment body."""
    expected_payload = '{"body": "[Original issue 1](https://github.com/webcompat/webcompat-tests/issues/1)"}'  # noqa
    json_event, signature = event_data('private_issue_opened.json')
    payload = json.loads(json_event)
    issue = WebHookIssue.from_dict(payload)
    assert issue.prepare_public_comment() == json.loads(
        expected_payload).get('body')


@pytest.mark.skip(reason="Outreach comment temporary disabled")
def test_prepare_outreach_comment():
    """Test we prepare the right comment body."""
    expected_payload = '{"body": "[Generate outreach template](https://webcompat.com/outreach/2598)"}'  # noqa
    json_event, signature = event_data('public_milestone_needscontact.json')
    payload = json.loads(json_event)
    issue = WebHookIssue.from_dict(payload, "https://webcompat.com/")
    assert issue.prepare_outreach_comment() == json.loads(
        expected_payload).get('body')


@pytest.mark.skip(reason="Outreach comment temporary disabled")
def test_prepare_outreach_comment_for_auth_report():
    """Test we prepare the right comment body."""
    expected_payload = '{"body": "[Generate outreach template](https://webcompat.com/outreach/2598)"}'  # noqa
    json_event, signature = event_data('public_milestone_needscontact_auth_report.json')    # noqa
    payload = json.loads(json_event)
    issue = WebHookIssue.from_dict(payload, "https://webcompat.com/")
    assert issue.prepare_outreach_comment() == json.loads(
        expected_payload).get('body')


def test_get_public_issue_number():
    """Test the extraction of the issue number from the public_url."""
    json_event, signature = event_data('private_issue_opened.json')
    payload = json.loads(json_event)
    issue = WebHookIssue.from_dict(payload)
    assert issue.get_public_issue_number() == '1'


@patch('webcompat.webhooks.model.make_request')
def test_tag_as_public(mock_mr):
    """Test tagging an issue as public."""
    json_event, signature = event_data('new_event_valid.json')
    payload = json.loads(json_event)
    issue = WebHookIssue.from_dict(payload)
    issue.tag_as_public()
    # make sure we modified the issue milestone property
    assert issue.milestone == 1
    method, uri, data = mock_mr.call_args[0]
    # make sure we sent a patch with the right data to GitHub
    assert method == 'patch'
    assert type(data) == dict
    assert 'labels' in data
    assert 'milestone' in data


@patch('webcompat.webhooks.helpers.extract_priority_label')
def test_prepare_accepted_issue(mock_priority):
    """Test the payload preparation for accepted moderated issues.

    Labels extraction will create a call to the topsites db
    and return a value. If the db has not been populated, the result
    will be different. So we return a value 'priority-critical' here.
    """
    mock_priority.return_value = 'priority-critical'
    json_event, signature = event_data('private_milestone_accepted.json')
    payload = json.loads(json_event)
    issue = WebHookIssue.from_dict(payload)
    actual = issue.prepare_accepted_issue()
    expected = {
        'body': '<!-- @browser: Firefox 55.0 -->\n'
        '<!-- @ua_header: Mozilla/5.0 (X11; Linux x86_64; rv:55.0) '
        'Gecko/20100101 Firefox/55.0 -->\n'
        '<!-- @reported_with: web -->\n'
        '<!-- @public_url: '
        'https://github.com/webcompat/webcompat-tests/issues/1  -->\n'
        '\n'
        '**URL**: https://www.netflix.com/',
        'labels': ['browser-firefox', 'priority-critical', 'engine-gecko'],
        'title': 'www.netflix.com - test private issue accepted'}
    assert expected == actual


@patch('webcompat.webhooks.helpers.extract_priority_label')
def test_prepare_accepted_issue(mock_priority):
    """Test the payload preparation for accepted: invalid moderated issues.
    """
    mock_priority.return_value = 'priority-critical'
    json_event, signature = event_data('private_milestone_accepted.json')
    payload = json.loads(json_event)
    issue = WebHookIssue.from_dict(payload)
    actual = issue.prepare_accepted_issue('invalid')
    expected = {
        'body': '<!-- @browser: Firefox 55.0 -->\n'
        '<!-- @ua_header: Mozilla/5.0 (X11; Linux x86_64; rv:55.0) '
        'Gecko/20100101 Firefox/55.0 -->\n'
        '<!-- @reported_with: web -->\n'
        '<!-- @public_url: '
        'https://github.com/webcompat/webcompat-tests/issues/1  -->\n'
        '\n'
        '**URL**: https://www.netflix.com/',
        'labels': ['browser-firefox', 'priority-critical', 'engine-gecko'],
        'title': 'www.netflix.com - test private issue accepted',
        'milestone': 8, 'state': 'closed'}
    assert expected == actual


@patch('webcompat.webhooks.helpers.extract_priority_label')
def test_prepare_accepted_issue(mock_priority):
    """Test the payload preparation for accepted: invalid moderated issues.
    """
    mock_priority.return_value = 'priority-critical'
    json_event, signature = event_data('private_milestone_accepted.json')
    payload = json.loads(json_event)
    issue = WebHookIssue.from_dict(payload)
    actual = issue.prepare_accepted_issue('incomplete')
    expected = {
        'body': '<!-- @browser: Firefox 55.0 -->\n'
        '<!-- @ua_header: Mozilla/5.0 (X11; Linux x86_64; rv:55.0) '
        'Gecko/20100101 Firefox/55.0 -->\n'
        '<!-- @reported_with: web -->\n'
        '<!-- @public_url: '
        'https://github.com/webcompat/webcompat-tests/issues/1  -->\n'
        '\n'
        '**URL**: https://www.netflix.com/',
        'labels': ['browser-firefox', 'priority-critical', 'engine-gecko'],
        'title': 'www.netflix.com - test private issue accepted',
        'milestone': 7, 'state': 'closed'}
    assert expected == actual


@patch('webcompat.webhooks.model.get_issue_classification')
@patch('webcompat.webhooks.model.make_request')
def test_process_issue_action_scenarios(mock_mr, mock_classification):
    """Test we are getting the right response for each scenario."""
    test_data = [
        ('new_event_valid.json', gracias),
        ('wrong_repo.json', wrong_repo),
        ('private_milestone_accepted_wrong_repo.json', wrong_repo),
        ('private_milestone_accepted.json', accepted),
        ('private_milestone_closed_unmoderated.json', rejected),
        ('private_milestone_accepted_incomplete.json', incomplete),
        ('private_milestone_accepted_invalid.json', invalid),
        ('private_issue_opened.json', comment_added),
        # ('public_milestone_needscontact.json', outreach_comment_added),
        ('private_milestone_ml_autoclosed.json', autoclosed),
    ]
    mock_classification.return_value = (
        {'prob': [0.03385603427886963, 0.9661439657211304], 'class': 1}
    )

    for issue_event, expected_rv in test_data:
        json_event, signature = event_data(issue_event)
        payload = json.loads(json_event)
        issue = WebHookIssue.from_dict(payload)
        with webcompat.app.test_request_context():
            rv = issue.process_issue_action()
            assert rv == expected_rv


@patch('webcompat.webhooks.model.make_request')
def test_process_issue_action_github_api_exception(mock_mr, caplog):
    """Test GitHub API exception handling.

    Each of the test scenarios have the following:
    issue_payload, expected_log, method
    method is unused in the test, but is meant to provide context to
    the reader for where the exception is happening.
    """
    caplog.set_level(logging.INFO)
    mock_mr.side_effect = HTTPError()
    mock_mr.status_code = 400
    scenarios = [
        ('private_milestone_accepted.json',
         'private:moving to public failed', 'moderate_private_issue'),
        ('private_issue_no_source.json', 'comment failed',
         'comment_public_uri'),
        ('new_event_valid.json', 'public:opened labels failed',
         'tag_as_public'),
        ('private_milestone_closed_unmoderated.json',
         'public rejection failed', 'close_public_issue'),
        ('private_milestone_accepted_invalid.json',
         'private:closing public issue as invalid failed',
         'close_public_issue'),
        ('private_milestone_accepted_incomplete.json',
         'private:closing public issue as incomplete failed',
         'close_public_issue'),
        ('private_milestone_ml_autoclosed.json',
         'private:closing public issue as invalid by ml-bot failed',
         'close_public_issue')
    ]
    for scenario in scenarios:
        issue_payload, expected_log, method = scenario
        json_event, signature = event_data(issue_payload)
        payload = json.loads(json_event)
        issue = WebHookIssue.from_dict(payload)
        with webcompat.app.test_request_context():
            rv = issue.process_issue_action()
            assert rv == oops
            assert expected_log in caplog.text


@patch('webcompat.webhooks.model.make_request')
@patch('webcompat.webhooks.model.WebHookIssue.close_public_issue')
def test_process_issue_action_close_scenarios(mock_close, mock_mr):
    """Test 3 scenarios that will result in a closed issue

    1. milestoned w/ accepted: incomplete
    2. milestoned w/ accepted: invalid
    3. closed as unmoderated
    And ensure it gets called with the right argument.
    """
    called = [
        ('private_milestone_closed_unmoderated.json', 'rejected'),
        ('private_milestone_accepted_incomplete.json', 'incomplete'),
        ('private_milestone_accepted_invalid.json', 'invalid'),
        ('private_milestone_ml_autoclosed.json', 'autoclosed'),
    ]
    for scenario in called:
        issue_payload, arg = scenario
        json_event, signature = event_data(issue_payload)
        payload = json.loads(json_event)
        issue = WebHookIssue.from_dict(payload)
        with webcompat.app.test_request_context():
            issue.process_issue_action()
            mock_close.assert_called_with(reason=arg)


@patch('webcompat.webhooks.model.get_issue_classification')
@patch('webcompat.webhooks.model.make_request')
@patch('webcompat.webhooks.model.WebHookIssue.close_public_issue')
def test_process_issue_action_not_closed_scenarios(mock_close, mock_mr, mock_classification):  # noqa
    """Test scenarios where close_public_issue is never called."""
    not_called = [
        'private_milestone_closed_invalid.json',
        'new_event_valid.json',
        'private_milestone_accepted_wrong_repo.json',
        'private_issue_opened.json'
    ]

    mock_classification.return_value = (
        {'prob': [0.03385603427886963, 0.9661439657211304], 'class': 1}
    )

    for scenario in not_called:
        json_event, signature = event_data(scenario)
        payload = json.loads(json_event)
        issue = WebHookIssue.from_dict(payload)
        with webcompat.app.test_request_context():
            issue.process_issue_action()
            mock_close.assert_not_called()


@patch('webcompat.webhooks.model.get_issue_classification')
@patch('webcompat.webhooks.model.make_request')
def test_classify_issue_probability_high(mock_mr, mock_classification):
    """Test classifying an issue and adding a label."""
    mock_classification.return_value = (
        {'prob': [0.03385603427886963, 0.9761439657211304], 'class': 1}
    )

    json_event, signature = event_data('private_issue_opened.json')
    payload = json.loads(json_event)
    issue = WebHookIssue.from_dict(payload)
    issue.classify()
    method, uri, data = mock_mr.call_args[0]

    # make sure we move the issue to ml-autoclosed milestone and
    # send a patch request to Github
    assert method == 'patch'
    assert type(data) == dict
    assert data.get('milestone') == AUTOCLOSED_MILESTONE_ID


@patch('webcompat.webhooks.model.get_issue_classification')
@patch('webcompat.webhooks.model.make_request')
def test_classify_issue_probability_low(mock_mr, mock_classification):
    """Test classifying and not setting a label.

    Use case when classification came back with probability threshold
    lower than minimum.
    """
    mock_classification.return_value = (
        {'prob': [0.03385603427886963, 0.8261439657211304], 'class': 1}
    )

    json_event, signature = event_data('private_issue_opened.json')
    payload = json.loads(json_event)
    issue = WebHookIssue.from_dict(payload)
    issue.classify()
    mock_mr.assert_not_called()


@patch('webcompat.webhooks.model.get_issue_classification')
@patch('webcompat.webhooks.model.make_request')
def test_classify_issue_needsdiagnosis_true(mock_mr, mock_classification):
    """Test classifying and not setting a label if needsdiagnosis=True."""
    mock_classification.return_value = (
        {'prob': [0.8261439657211304, 0.03385603427886963], 'class': 0}
    )

    json_event, signature = event_data('private_issue_opened.json')
    payload = json.loads(json_event)
    issue = WebHookIssue.from_dict(payload)
    issue.classify()
    mock_mr.assert_not_called()


@patch('webcompat.webhooks.ml.make_classification_request')
@patch('webcompat.webhooks.model.make_request')
def test_classify_issue_service_exception(mock_mr, mock_classification, caplog):        # noqa
    """Test that ml server error exception handled gracefully."""
    caplog.set_level(logging.INFO)
    mock_classification.side_effect = HTTPError()
    json_event, signature = event_data('private_issue_opened.json')
    payload = json.loads(json_event)
    issue = WebHookIssue.from_dict(payload)
    with webcompat.app.test_request_context():
        rv = issue.process_issue_action()
        assert rv == oops
        assert 'classification failed' in caplog.text
