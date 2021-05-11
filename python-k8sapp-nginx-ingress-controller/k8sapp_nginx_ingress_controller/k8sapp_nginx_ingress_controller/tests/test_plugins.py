#
# Copyright (c) 2021 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

from sysinv.tests.db import base


class NginxICTestCase(base.DbTestCase):
    def setUp(self):
        super(NginxICTestCase, self).setUp()

    def tearDown(self):
        super(NginxICTestCase, self).tearDown()

    def test_plugins(self):
        # placeholder for future unit tests
        pass
