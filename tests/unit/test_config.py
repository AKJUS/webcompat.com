#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Tests for the config functions."""

import json
import os
import unittest

from config import update_status_config
from config import get_variation
from webcompat import webcompat


def json_data(filename):
    """Return a tuple with the content and its signature."""
    current_root = os.path.realpath(os.curdir)
    fixtures_path = 'tests/fixtures/config'
    path = os.path.join(current_root, fixtures_path, filename)
    with open(path, 'r') as f:
        json_event = json.dumps(json.load(f))
    return json_event


class TestConfig(unittest.TestCase):
    """Test for Config file in the the project."""

    def setUp(self):
        """Set up the tests."""
        webcompat.app.config['TESTING'] = True
        self.app = webcompat.app.test_client()

    def tearDown(self):
        """Tear down the tests."""
        pass

    def test_update_status_config(self):
        """Update statuses with real milestones id."""
        expected = {'sitewait': {'state': 'open', 'id': 5, 'order': 5}, 'worksforme': {'state': 'closed', 'id': 11, 'order': 8}, 'non-compat': {'state': 'closed', 'id': 12, 'order': 6}, 'needsdiagnosis': {'state': 'open', 'id': 2, 'order': 2}, 'contactready': {'state': 'open', 'id': 4, 'order': 4}, 'wontfix': {'state': 'closed', 'id': 6, 'order': 7}, 'needscontact': {'state': 'open', 'id': 3, 'order': 3}, 'invalid': {'state': 'closed', 'id': 8, 'order': 4}, 'needstriage': {'state': 'open', 'id': 1, 'order': 1}, 'duplicate': {'state': 'closed', 'id': 10, 'order': 1}, 'fixed': {'state': 'closed', 'id': 9, 'order': 2}, 'incomplete': {'state': 'closed', 'id': 7, 'order': 3}, 'moved': {'state': 'closed', 'id': 13, 'order': 5}}  # noqa
        # Normal Case
        milestones_json = json_data('milestones_content.json')
        actual = update_status_config(milestones_json)
        self.assertDictEqual(actual, expected)
        # Missing a milestone
        milestones_json = json_data('milestones_content_missing.json')
        actual = update_status_config(milestones_json)
        self.assertNotEqual(actual, expected)
        self.assertIsNone(actual)
        # Unknown milestone added to the project
        milestones_json = json_data('milestones_content_plus.json')
        actual = update_status_config(milestones_json)
        self.assertEqual(actual, expected)

    def test_get_variation(self):
        """
        Check the conversion from string to tuples of two int.
        """
        defs = {'a': (1, 2)}
        self.assertTupleEqual((1, 2), get_variation('a', {'a': '1 2'}, defs))
        self.assertTupleEqual((1, 2), get_variation('a', {'a': None}, defs))
        self.assertTupleEqual((1, 2), get_variation('a', {'a': ''}, defs))
        self.assertTupleEqual((1, 2), get_variation('a', {'a': 2}, defs))
        self.assertTupleEqual((1, 2), get_variation('a', {'a': '1 2 3'}, defs))
        self.assertTupleEqual((1, 2), get_variation('a', {'a': '1 '}, defs))
        self.assertTupleEqual((1, 2),
                              get_variation('a', {'a': '  1 2 '}, defs))


if __name__ == '__main__':
    unittest.main()
