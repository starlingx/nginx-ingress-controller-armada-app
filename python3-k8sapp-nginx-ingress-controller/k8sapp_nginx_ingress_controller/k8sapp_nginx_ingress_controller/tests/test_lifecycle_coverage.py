#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
"""Tests for NginxIngressControllerAppLifecycleOperator."""

import mock
import unittest

from k8sapp_nginx_ingress_controller.lifecycle \
    import lifecycle_nginx_ingress_controller as lifecycle_mod
from k8sapp_nginx_ingress_controller.lifecycle \
    .lifecycle_nginx_ingress_controller \
    import NginxIngressControllerAppLifecycleOperator \
    as NginxICOperator
from sysinv.common import constants
from sysinv.common import exception
from sysinv.helm import lifecycle_hook
from sysinv.helm.lifecycle_constants import LifecycleConstants


class TestLifecycleActions(unittest.TestCase):
    """Test app_lifecycle_actions dispatch logic."""

    def setUp(self):
        super(TestLifecycleActions, self).setUp()
        self.operator = NginxICOperator()
        self.app_op = mock.MagicMock()
        self.app = mock.MagicMock()
        self.app.name = constants.HELM_APP_NGINX_IC

    def _make_hook(self, lifecycle_type, operation, timing):
        """Create a LifecycleHookInfo with given params.

        lifecycle_type - the lifecycle type constant
        operation - the app operation constant
        timing - the lifecycle timing constant

        Returns a configured LifecycleHookInfo instance.
        """
        hook = lifecycle_hook.LifecycleHookInfo()
        hook.init(
            LifecycleConstants.APP_LIFECYCLE_MODE_AUTO,
            lifecycle_type, timing, operation
        )
        return hook

    @mock.patch.object(NginxICOperator, 'pre_apply')
    def test_dispatch_pre_apply(self, mock_pre_apply):
        """Test dispatch to pre_apply."""
        hook = self._make_hook(
            LifecycleConstants.APP_LIFECYCLE_TYPE_RESOURCE,
            constants.APP_APPLY_OP,
            LifecycleConstants.APP_LIFECYCLE_TIMING_PRE
        )
        self.operator.app_lifecycle_actions(
            None, None, self.app_op, self.app, hook
        )
        mock_pre_apply.assert_called_once()

    @mock.patch.object(NginxICOperator, 'pre_backup')
    def test_dispatch_pre_backup(self, mock_pre_backup):
        """Test dispatch to pre_backup."""
        hook = self._make_hook(
            LifecycleConstants.APP_LIFECYCLE_TYPE_OPERATION,
            constants.APP_BACKUP,
            LifecycleConstants.APP_LIFECYCLE_TIMING_PRE
        )
        self.operator.app_lifecycle_actions(
            None, None, self.app_op, self.app, hook
        )
        mock_pre_backup.assert_called_once()

    @mock.patch.object(NginxICOperator, 'post_backup')
    def test_dispatch_post_backup(self, mock_post_backup):
        """Test dispatch to post_backup."""
        hook = self._make_hook(
            LifecycleConstants.APP_LIFECYCLE_TYPE_OPERATION,
            constants.APP_BACKUP,
            LifecycleConstants.APP_LIFECYCLE_TIMING_POST
        )
        self.operator.app_lifecycle_actions(
            None, None, self.app_op, self.app, hook
        )
        mock_post_backup.assert_called_once()

    @mock.patch.object(NginxICOperator, 'post_restore')
    def test_dispatch_post_restore(self, mock_post_restore):
        """Test dispatch to post_restore."""
        hook = self._make_hook(
            LifecycleConstants.APP_LIFECYCLE_TYPE_OPERATION,
            constants.APP_RESTORE,
            LifecycleConstants.APP_LIFECYCLE_TIMING_POST
        )
        self.operator.app_lifecycle_actions(
            None, None, self.app_op, self.app, hook
        )
        mock_post_restore.assert_called_once()

    def test_dispatch_falls_through_to_super(self):
        """Test unhandled hook falls through to super."""
        hook = self._make_hook(
            LifecycleConstants.APP_LIFECYCLE_TYPE_OPERATION,
            constants.APP_APPLY_OP,
            LifecycleConstants.APP_LIFECYCLE_TIMING_POST
        )
        # super().app_lifecycle_actions should not raise
        self.operator.app_lifecycle_actions(
            None, None, self.app_op, self.app, hook
        )


class TestPreBackup(unittest.TestCase):
    """Test pre_backup method."""

    def setUp(self):
        super(TestPreBackup, self).setUp()
        self.operator = NginxICOperator()
        self.app_op = mock.MagicMock()
        self.app = mock.MagicMock()
        self.app.name = constants.HELM_APP_NGINX_IC

    @mock.patch.object(
        NginxICOperator, '_update_helm_user_overrides')
    @mock.patch.object(
        NginxICOperator, '_delete_webhook_configuration')
    @mock.patch.object(
        NginxICOperator, '_get_webhook_configuration')
    @mock.patch.object(
        NginxICOperator, '_get_helm_user_overrides')
    def test_pre_backup_with_webhook(
        self, mock_get_overrides, mock_get_webhook,
        mock_delete_webhook, mock_update_overrides
    ):
        """Test pre_backup when webhook exists."""
        webhook = mock.MagicMock()
        webhook.metadata.name = 'test-webhook'
        mock_get_webhook.return_value = webhook
        mock_get_overrides.return_value = (
            "controller:\n"
            "  admissionWebhooks:\n"
            "    enabled: true\n"
        )

        self.operator.pre_backup(
            self.app_op, self.app
        )

        mock_delete_webhook.assert_called_once_with(
            self.app_op, 'test-webhook'
        )
        mock_update_overrides.assert_called_once()

    @mock.patch.object(
        NginxICOperator, '_delete_webhook_configuration')
    @mock.patch.object(
        NginxICOperator, '_get_webhook_configuration')
    def test_pre_backup_no_webhook(
        self, mock_get_webhook, mock_delete_webhook
    ):
        """Test pre_backup when no webhook exists."""
        mock_get_webhook.return_value = None

        self.operator.pre_backup(
            self.app_op, self.app
        )

        mock_delete_webhook.assert_not_called()

    @mock.patch.object(
        NginxICOperator, '_update_helm_user_overrides')
    @mock.patch.object(
        NginxICOperator, '_delete_webhook_configuration')
    @mock.patch.object(
        NginxICOperator, '_get_webhook_configuration')
    @mock.patch.object(
        NginxICOperator, '_get_helm_user_overrides')
    def test_pre_backup_override_content(
        self, mock_get_overrides, mock_get_webhook,
        mock_delete_webhook, mock_update_overrides
    ):
        """Test pre_backup modifies overrides correctly."""
        webhook = mock.MagicMock()
        webhook.metadata.name = 'test-webhook'
        mock_get_webhook.return_value = webhook
        original = (
            "controller:\n"
            "  admissionWebhooks:\n"
            "    enabled: true\n"
        )
        mock_get_overrides.return_value = original

        self.operator.pre_backup(
            self.app_op, self.app
        )

        call_args = mock_update_overrides.call_args
        updated_overrides = call_args[0][4]
        self.assertIn(
            lifecycle_mod
            .REAPPLY_ADMISSION_WEBHOOK_OVERRIDE,
            updated_overrides
        )
        self.assertIn(
            lifecycle_mod
            .DISABLE_ADMISSION_WEBHOOK_OVERRIDE_CREATION,
            updated_overrides
        )


class TestPostBackup(unittest.TestCase):
    """Test post_backup method."""

    def setUp(self):
        super(TestPostBackup, self).setUp()
        self.operator = NginxICOperator()
        self.app_op = mock.MagicMock()
        self.app = mock.MagicMock()
        self.app.name = constants.HELM_APP_NGINX_IC

    @mock.patch.object(
        NginxICOperator,
        '_recreate_webhook_configuration')
    def test_post_backup_calls_recreate(
        self, mock_recreate_webhook
    ):
        """Test post_backup delegates to recreate."""
        self.operator.post_backup(
            self.app_op, self.app
        )
        mock_recreate_webhook.assert_called_once_with(
            self.app_op, self.app
        )


class TestPostRestore(unittest.TestCase):
    """Test post_restore method."""

    def setUp(self):
        super(TestPostRestore, self).setUp()
        self.operator = NginxICOperator()
        self.app_op = mock.MagicMock()
        self.app = mock.MagicMock()
        self.app.name = constants.HELM_APP_NGINX_IC

    @mock.patch.object(
        NginxICOperator,
        '_recreate_webhook_configuration')
    def test_post_restore_calls_recreate(
        self, mock_recreate_webhook
    ):
        """Test post_restore delegates to recreate."""
        self.operator.post_restore(
            self.app_op, self.app
        )
        mock_recreate_webhook.assert_called_once_with(
            self.app_op, self.app
        )


class TestGetWebhookConfiguration(unittest.TestCase):
    """Test _get_webhook_configuration method."""

    def setUp(self):
        super(
            TestGetWebhookConfiguration, self
        ).setUp()
        self.operator = NginxICOperator()
        self.app_op = mock.MagicMock()

    def test_no_webhooks_found(self):
        """Test returns None when no webhooks found."""
        kube = self.app_op._kube
        kube.list_custom_resources.return_value = []
        result = self.operator \
            ._get_webhook_configuration(self.app_op)
        self.assertIsNone(result)

    def test_multiple_webhooks_raises(self):
        """Test raises when multiple webhooks found."""
        kube = self.app_op._kube
        kube.list_custom_resources.return_value = [
            mock.MagicMock(), mock.MagicMock()
        ]
        self.assertRaises(
            exception.LifecycleSemanticCheckException,
            self.operator._get_webhook_configuration,
            self.app_op
        )

    def test_single_webhook_returns_deserialized(self):
        """Test returns deserialized webhook."""
        webhook_data = mock.MagicMock()
        kube = self.app_op._kube
        kube.list_custom_resources.return_value = [
            webhook_data
        ]
        admission_api = (
            kube
            ._get_kubernetesclient_admission_registration
            .return_value
        )
        api_client = admission_api.api_client
        expected_webhook = mock.MagicMock()
        deserialize = (
            api_client._ApiClient__deserialize
        )
        deserialize.return_value = expected_webhook

        result = self.operator \
            ._get_webhook_configuration(self.app_op)

        self.assertEqual(result, expected_webhook)
        deserialize.assert_called_once_with(
            webhook_data,
            'V1beta1ValidatingWebhookConfiguration'
        )


class TestDeleteWebhookConfiguration(unittest.TestCase):
    """Test _delete_webhook_configuration method."""

    def setUp(self):
        super(
            TestDeleteWebhookConfiguration, self
        ).setUp()
        self.operator = NginxICOperator()
        self.app_op = mock.MagicMock()

    def test_delete_calls_kube(self):
        """Test delete delegates to kube client."""
        self.operator._delete_webhook_configuration(
            self.app_op, 'my-webhook'
        )
        kube = self.app_op._kube
        delete_method = (
            kube
            .kube_delete_validating_webhook_configuration
        )
        delete_method.assert_called_once_with(
            'my-webhook'
        )


class TestRecreateWebhookConfiguration(unittest.TestCase):
    """Test _recreate_webhook_configuration method."""

    def setUp(self):
        super(
            TestRecreateWebhookConfiguration, self
        ).setUp()
        self.operator = NginxICOperator()
        self.app_op = mock.MagicMock()
        self.app = mock.MagicMock()
        self.app.name = constants.HELM_APP_NGINX_IC

    @mock.patch.object(
        NginxICOperator, '_get_webhook_configuration')
    def test_webhook_already_present(
        self, mock_get_webhook
    ):
        """Test returns early if webhook exists."""
        mock_get_webhook.return_value = mock.MagicMock()
        self.operator._recreate_webhook_configuration(
            self.app_op, self.app
        )
        app_get = self.app_op._dbapi.kube_app_get
        app_get.assert_not_called()

    @mock.patch.object(
        NginxICOperator, '_get_helm_user_overrides')
    @mock.patch.object(
        NginxICOperator, '_get_webhook_configuration')
    def test_no_reapply_flag(
        self, mock_get_webhook, mock_get_overrides
    ):
        """Test returns early if no reapply flag."""
        mock_get_webhook.return_value = None
        mock_get_overrides.return_value = (
            "some: override\n"
        )

        self.operator._recreate_webhook_configuration(
            self.app_op, self.app
        )

        perform_apply = self.app_op.perform_app_apply
        perform_apply.assert_not_called()

    @mock.patch.object(
        NginxICOperator, '_update_helm_user_overrides')
    @mock.patch.object(
        NginxICOperator, '_get_helm_user_overrides')
    @mock.patch.object(
        NginxICOperator, '_get_webhook_configuration')
    def test_recreate_with_reapply_flag(
        self, mock_get_webhook,
        mock_get_overrides, mock_update_overrides
    ):
        """Test full recreate flow with reapply flag."""
        mock_get_webhook.return_value = None
        reapply_override = (
            lifecycle_mod
            .REAPPLY_ADMISSION_WEBHOOK_OVERRIDE
        )
        disable_override = (
            lifecycle_mod
            .DISABLE_ADMISSION_WEBHOOK_OVERRIDE_CREATION
        )
        overrides = (
            reapply_override
            + disable_override
            + "extra: value\n"
        )
        mock_get_overrides.return_value = overrides

        self.operator._recreate_webhook_configuration(
            self.app_op, self.app
        )

        perform_apply = self.app_op.perform_app_apply
        perform_apply.assert_called_once()
        self.assertEqual(
            mock_update_overrides.call_count, 2
        )

    @mock.patch.object(
        NginxICOperator, '_update_helm_user_overrides')
    @mock.patch.object(
        NginxICOperator, '_get_helm_user_overrides')
    @mock.patch.object(
        NginxICOperator, '_get_webhook_configuration')
    def test_recreate_restores_backup_override(
        self, mock_get_webhook,
        mock_get_overrides, mock_update_overrides
    ):
        """Test recreate restores backup overrides."""
        mock_get_webhook.return_value = None
        reapply_override = (
            lifecycle_mod
            .REAPPLY_ADMISSION_WEBHOOK_OVERRIDE
        )
        disable_override = (
            lifecycle_mod
            .DISABLE_ADMISSION_WEBHOOK_OVERRIDE_CREATION
        )
        backup_override = (
            lifecycle_mod
            .BACKUP_ADMISSION_WEBHOOK_OVERRIDE
        )
        overrides = (
            reapply_override
            + disable_override
            + backup_override
            + ": true\n"
        )
        mock_get_overrides.return_value = overrides

        self.operator._recreate_webhook_configuration(
            self.app_op, self.app
        )

        final_call = (
            mock_update_overrides.call_args_list[-1]
        )
        final_overrides = final_call[0][4]
        self.assertNotIn(
            lifecycle_mod.BACKUP_FLAG,
            final_overrides
        )


class TestGetHelmUserOverrides(unittest.TestCase):
    """Test _get_helm_user_overrides method."""

    def setUp(self):
        super(
            TestGetHelmUserOverrides, self
        ).setUp()
        self.operator = NginxICOperator()

    def test_returns_overrides(self):
        """Test returns user_overrides string."""
        mock_dbapi = mock.MagicMock()
        mock_app = mock.MagicMock()
        mock_app.id = 1
        override_obj = mock.MagicMock()
        override_obj.user_overrides = "test: value"
        mock_dbapi.helm_override_get.return_value = (
            override_obj
        )

        result = self.operator._get_helm_user_overrides(
            mock_dbapi, mock_app, 'chart', 'ns'
        )
        self.assertEqual(result, "test: value")

    def test_returns_empty_on_none(self):
        """Test returns empty string when None."""
        mock_dbapi = mock.MagicMock()
        mock_app = mock.MagicMock()
        mock_app.id = 1
        override_obj = mock.MagicMock()
        override_obj.user_overrides = None
        mock_dbapi.helm_override_get.return_value = (
            override_obj
        )

        result = self.operator._get_helm_user_overrides(
            mock_dbapi, mock_app, 'chart', 'ns'
        )
        self.assertEqual(result, "")

    def test_returns_empty_on_not_found(self):
        """Test returns empty string when not found."""
        mock_dbapi = mock.MagicMock()
        mock_app = mock.MagicMock()
        mock_app.id = 1
        mock_dbapi.helm_override_get.side_effect = \
            exception.HelmOverrideNotFound(
                name='chart', namespace='ns'
            )

        result = self.operator._get_helm_user_overrides(
            mock_dbapi, mock_app, 'chart', 'ns'
        )
        self.assertEqual(result, "")


class TestUpdateHelmUserOverrides(unittest.TestCase):
    """Test _update_helm_user_overrides method."""

    def setUp(self):
        super(
            TestUpdateHelmUserOverrides, self
        ).setUp()
        self.operator = NginxICOperator()

    def test_calls_helm_override_update(self):
        """Test delegates to helm_override_update."""
        mock_dbapi = mock.MagicMock()
        mock_app = mock.MagicMock()
        mock_app.id = 42

        self.operator._update_helm_user_overrides(
            mock_dbapi, mock_app,
            'chart', 'ns', 'new-overrides'
        )

        mock_dbapi.helm_override_update \
            .assert_called_once_with(
                app_id=42,
                name='chart',
                namespace='ns',
                values={
                    'user_overrides': 'new-overrides'
                }
            )
