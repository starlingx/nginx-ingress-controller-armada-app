#
# Copyright (c) 2021 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

import json
import mock

from k8sapp_nginx_ingress_controller.common import constants as app_constants
from k8sapp_nginx_ingress_controller.lifecycle.lifecycle_nginx_ingress_controller \
    import NginxIngressControllerAppLifecycleOperator as NginxICOperator
from sysinv.common import constants
from sysinv.db import api as db_api
from sysinv.helm import lifecycle_hook
from sysinv.tests.db import base
from sysinv.tests.db import utils as dbutils


class NginxICTestCase(base.DbTestCase):
    def setUp(self):
        super(NginxICTestCase, self).setUp()

        self.dbapi = db_api.get_instance()
        self.app_op = mock.MagicMock()
        self.new_app = mock.MagicMock()

        self.new_app.id = 2
        self.new_app.name = constants.HELM_APP_NGINX_IC

        self.old_db_app = dbutils.create_test_app(
            id=1,
            name=constants.HELM_APP_NGINX_IC,
            app_version='1.0-0')
        # creating an inactive app does not work, need to update the status later
        self.dbapi.kube_app_update(self.old_db_app.id, {'status': constants.APP_INACTIVE_STATE})

        self.new_db_app = dbutils.create_test_app(
            id=self.new_app.id,
            status=constants.APP_APPLY_IN_PROGRESS,
            name=constants.HELM_APP_NGINX_IC,
            app_version='1.1-1')

        self.hook_info = lifecycle_hook.LifecycleHookInfo()
        self.hook_info.init(
            constants.APP_LIFECYCLE_MODE_AUTO,
            constants.APP_LIFECYCLE_TYPE_RESOURCE,
            constants.APP_LIFECYCLE_TIMING_PRE,
            constants.APP_APPLY_OP)

        self.old_overrides = {
            'udp': {
                '161': 'kube-system/snmpd-service:161'
            },
            'tcp': {
                '162': 'kube-system/snmpd-service:162'
            }
        }

        self.new_overrides = {
            'host': 'dummy-service.host.wrs.com'
        }

    def tearDown(self):
        super(NginxICTestCase, self).tearDown()

    def test_has_old_override_no_new_override(self):
        """Test that overrides are properly migrated.

        Test that if the old app version has an override and the
        new app version does not, the old override is migrated to the
        new version.
        """
        dbutils.create_test_helm_overrides(
            app_id=self.old_db_app.id,
            name=app_constants.HELM_CHART_LEGACY_INGRESS_NGINX,
            namespace=app_constants.HELM_NS_NGINX_INGRESS_CONTROLLER,
            user_overrides=json.dumps(self.old_overrides))

        dbutils.create_test_helm_overrides(
            app_id=self.new_db_app.id,
            name=app_constants.HELM_CHART_INGRESS_NGINX,
            namespace=app_constants.HELM_NS_NGINX_INGRESS_CONTROLLER,
            user_overrides=None)

        lifecycleOperator = NginxICOperator()
        lifecycleOperator.app_lifecycle_actions(None, None, self.app_op, self.new_app, self.hook_info)

        overrides = self.dbapi.helm_override_get(
            app_id=self.new_app.id,
            name=app_constants.HELM_CHART_INGRESS_NGINX,
            namespace=app_constants.HELM_NS_NGINX_INGRESS_CONTROLLER)

        self.assertEqual(self.old_overrides, json.loads(overrides['user_overrides']))

    def test_has_no_old_override_no_new_override(self):
        """Test that no overrides are migrated.

        Test that if the old app version does not trigger migration
        when no override is present
        """
        old_overrides = None

        dbutils.create_test_helm_overrides(
            app_id=self.old_db_app.id,
            name=app_constants.HELM_CHART_LEGACY_INGRESS_NGINX,
            namespace=app_constants.HELM_NS_NGINX_INGRESS_CONTROLLER)

        dbutils.create_test_helm_overrides(
            app_id=self.new_db_app.id,
            name=app_constants.HELM_CHART_INGRESS_NGINX,
            namespace=app_constants.HELM_NS_NGINX_INGRESS_CONTROLLER,
            user_overrides=None)

        lifecycleOperator = NginxICOperator()
        lifecycleOperator.app_lifecycle_actions(None, None, self.app_op, self.new_app, self.hook_info)

        overrides = self.dbapi.helm_override_get(
            app_id=self.new_app.id,
            name=app_constants.HELM_CHART_INGRESS_NGINX,
            namespace=app_constants.HELM_NS_NGINX_INGRESS_CONTROLLER)

        self.assertEqual(old_overrides, overrides['user_overrides'])

    def test_has_old_override_new_override(self):
        """Test that no overrides are migrated.

        Test that the migration does not occur when a override
        is present in the new version
        """

        dbutils.create_test_helm_overrides(
            app_id=self.old_db_app.id,
            name=app_constants.HELM_CHART_LEGACY_INGRESS_NGINX,
            namespace=app_constants.HELM_NS_NGINX_INGRESS_CONTROLLER,
            user_overrides=json.dumps(self.old_overrides))

        dbutils.create_test_helm_overrides(
            app_id=self.new_db_app.id,
            name=app_constants.HELM_CHART_INGRESS_NGINX,
            namespace=app_constants.HELM_NS_NGINX_INGRESS_CONTROLLER,
            user_overrides=json.dumps(self.new_overrides))

        lifecycleOperator = NginxICOperator()
        lifecycleOperator.app_lifecycle_actions(None, None, self.app_op, self.new_app, self.hook_info)

        overrides = self.dbapi.helm_override_get(
            app_id=self.new_app.id,
            name=app_constants.HELM_CHART_INGRESS_NGINX,
            namespace=app_constants.HELM_NS_NGINX_INGRESS_CONTROLLER)

        self.assertEqual(self.new_overrides, json.loads(overrides['user_overrides']))

    def test_has_no_old_app(self):
        """Test that no overrides are migrated.

        Test if new application is successfully applied with
        overrides when no previous version is present
        """

        self.dbapi.kube_app_destroy(
            name=self.old_db_app.name,
            version=self.old_db_app.app_version,
            inactive=True,
        )

        dbutils.create_test_helm_overrides(
            app_id=self.new_db_app.id,
            name=app_constants.HELM_CHART_INGRESS_NGINX,
            namespace=app_constants.HELM_NS_NGINX_INGRESS_CONTROLLER,
            user_overrides=json.dumps(self.new_overrides))

        lifecycleOperator = NginxICOperator()
        lifecycleOperator.app_lifecycle_actions(None, None, self.app_op, self.new_app, self.hook_info)

        overrides = self.dbapi.helm_override_get(
            app_id=self.new_app.id,
            name=app_constants.HELM_CHART_INGRESS_NGINX,
            namespace=app_constants.HELM_NS_NGINX_INGRESS_CONTROLLER)

        self.assertEqual(self.new_overrides, json.loads(overrides['user_overrides']))
