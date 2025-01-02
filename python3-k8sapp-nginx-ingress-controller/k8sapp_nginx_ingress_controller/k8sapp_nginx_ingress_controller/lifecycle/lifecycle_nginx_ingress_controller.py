#
# Copyright (c) 2021 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
# All Rights Reserved.
#

"""System inventory App lifecycle operator."""

from time import time

from k8sapp_nginx_ingress_controller.common import constants as app_constants
from oslo_log import log as logging
from sysinv.common import constants
from sysinv.common import exception
from sysinv.db import api as dbapi
from sysinv.helm import lifecycle_base as base
from sysinv.helm.lifecycle_constants import LifecycleConstants
from sysinv.helm.lifecycle_hook import LifecycleHookInfo
from sysinv.helm import lifecycle_utils

LOG = logging.getLogger(__name__)

BACKUP_FLAG = "backup_"
CREATE_ADMISSION_WEBHOOK_OVERRIDE = "controller:\n  admissionWebhooks:\n    enabled"

# Used as a flag to short-circuit webhook creation logic during post-backup and
# post-restore. This name has no previous significance; it is introduced here.
REAPPLY_ADMISSION_WEBHOOK_OVERRIDE = "ReapplyAdmissionWebhook: true\n"

# It is necessary to disable the webhook creation in order to prevent it from
# being created too early. Explicitly set the chart value "enabled" to false.
# Compare CREATE_ADMISSION_WEBHOOK_OVERRIDE + ': true".
DISABLE_ADMISSION_WEBHOOK_OVERRIDE_CREATION = CREATE_ADMISSION_WEBHOOK_OVERRIDE + ": false\n"

# Swapping out the enabled webhook with a "backup" name in order to simplify
# recreating it. The user overrides are presented as a string, so
# CREATE_ADMISSION_WEBHOOK_OVERRIDE is replaced with
# BACKUP_ADMISSION_WEBHOOK_OVERRIDE in pre-backup, and restored in post-backup
# and post-restore operations.
BACKUP_ADMISSION_WEBHOOK_OVERRIDE = BACKUP_FLAG + CREATE_ADMISSION_WEBHOOK_OVERRIDE


class NginxIngressControllerAppLifecycleOperator(base.AppLifecycleOperator):
    def app_lifecycle_actions(self, context, conductor_obj, app_op, app, hook_info):
        """Perform lifecycle actions for an operation

        :param context: request context, can be None
        :param conductor_obj: conductor object, can be None
        :param app_op: AppOperator object
        :param app: AppOperator.Application object
        :param hook_info: LifecycleHookInfo object

        """
        if hook_info.lifecycle_type == LifecycleConstants.APP_LIFECYCLE_TYPE_RESOURCE:
            if hook_info.operation == constants.APP_APPLY_OP:
                if hook_info.relative_timing == LifecycleConstants.APP_LIFECYCLE_TIMING_PRE:
                    return self.pre_apply(app_op, app, hook_info)

        if hook_info.lifecycle_type == LifecycleConstants.APP_LIFECYCLE_TYPE_OPERATION:
            if hook_info.operation == constants.APP_BACKUP:
                if hook_info.relative_timing == LifecycleConstants.APP_LIFECYCLE_TIMING_PRE:
                    return self.pre_backup(app_op, app)

        if hook_info.lifecycle_type == LifecycleConstants.APP_LIFECYCLE_TYPE_OPERATION:
            if hook_info.operation == constants.APP_BACKUP:
                if hook_info.relative_timing == LifecycleConstants.APP_LIFECYCLE_TIMING_POST:
                    return self.post_backup(app_op, app)

        if hook_info.lifecycle_type == LifecycleConstants.APP_LIFECYCLE_TYPE_OPERATION:
            if hook_info.operation == constants.APP_RESTORE:
                if hook_info.relative_timing == LifecycleConstants.APP_LIFECYCLE_TIMING_POST:
                    return self.post_restore(app_op, app)

        super(NginxIngressControllerAppLifecycleOperator, self).app_lifecycle_actions(
            context, conductor_obj, app_op, app, hook_info)

    def pre_apply(self, app_op, app, hook_info):
        """Pre Apply actions

        Creates the local registry secret and migrates helm user overrides
        from one chart name to another

        :param app_op: AppOperator object
        :param app: AppOperator.Application object
        :param hook_info: LifecycleHookInfo object
        """
        LOG.debug("Executing pre_apply for {} app".format(constants.HELM_APP_NGINX_IC))

        # As this overrides the functionality provided in the base class, make
        # sure we perform the operations defined there
        lifecycle_utils.create_local_registry_secrets(app_op, app, hook_info)

        dbapi_instance = dbapi.get_instance()

        # get most recently created inactive app
        inactive_db_apps = dbapi_instance.kube_app_get_inactive(
            app.name, limit=1, sort_key='created_at', sort_dir='desc')

        if not inactive_db_apps:
            # nothing to migrate from
            return

        from_db_app = inactive_db_apps[0]
        to_db_app = dbapi_instance.kube_app_get(app.name)

        old_chart_overrides = self._get_helm_user_overrides(
            dbapi_instance,
            from_db_app,
            app_constants.HELM_CHART_LEGACY_INGRESS_NGINX,
            app_constants.HELM_NS_NGINX_INGRESS_CONTROLLER)

        new_chart_overrides = self._get_helm_user_overrides(
            dbapi_instance,
            to_db_app,
            app_constants.HELM_CHART_INGRESS_NGINX,
            app_constants.HELM_NS_NGINX_INGRESS_CONTROLLER)

        if old_chart_overrides and not new_chart_overrides:
            # if there are user overrides on the old chart name and there are no user overrides
            # on the new chart name, migrate them from the old to the new name
            # we do not want to do the migration if there are overrides for the new name because
            # that means the user has already done it.
            LOG.info("Migrating user_overrides from {} to {}".format(
                app_constants.HELM_CHART_LEGACY_INGRESS_NGINX, app_constants.HELM_CHART_INGRESS_NGINX))

            self._update_helm_user_overrides(
                dbapi_instance,
                to_db_app,
                app_constants.HELM_CHART_INGRESS_NGINX,
                app_constants.HELM_NS_NGINX_INGRESS_CONTROLLER,
                old_chart_overrides,
            )

    def pre_backup(self, app_op, app):
        LOG.debug("Executing pre_backup for {} app".format(constants.HELM_APP_NGINX_IC))

        webhook = self._get_webhook_configuration(app_op)
        if not webhook:
            LOG.info("Validating webhook not present on system. Nothing to be done.")
            return

        webhook_name = webhook.metadata.name
        self._delete_webhook_configuration(app_op, webhook_name)

        dbapi_instance = app_op._dbapi
        db_app = dbapi_instance.kube_app_get(app.name)

        user_overrides = self._get_helm_user_overrides(
            dbapi_instance,
            db_app,
            app_constants.HELM_CHART_INGRESS_NGINX,
            app_constants.HELM_NS_NGINX_INGRESS_CONTROLLER,
        )

        updated_overrides = (
            REAPPLY_ADMISSION_WEBHOOK_OVERRIDE
            + DISABLE_ADMISSION_WEBHOOK_OVERRIDE_CREATION
            + user_overrides.replace(
                CREATE_ADMISSION_WEBHOOK_OVERRIDE,
                BACKUP_ADMISSION_WEBHOOK_OVERRIDE,
            )
        )

        self._update_helm_user_overrides(
            dbapi_instance,
            db_app,
            app_constants.HELM_CHART_INGRESS_NGINX,
            app_constants.HELM_NS_NGINX_INGRESS_CONTROLLER,
            updated_overrides,
        )

    def post_backup(self, app_op, app):
        LOG.debug(
            "Executing post_backup for {} app".format(constants.HELM_APP_NGINX_IC)
        )
        self._recreate_webhook_configuration(app_op, app)

    def post_restore(self, app_op, app):
        LOG.debug(
            "Executing post_restore for {} app".format(constants.HELM_APP_NGINX_IC)
        )
        self._recreate_webhook_configuration(app_op, app)

    def _get_webhook_configuration(self, app_op):
        label_selector = (
            "app.kubernetes.io/name={},"
            "app.kubernetes.io/component={}".format(
                app_constants.HELM_CHART_INGRESS_NGINX, "admission-webhook"
            )
        )

        # pylint: disable=fixme
        # FIXME(outbrito): Workaround to deal with k8s upvesion to >=1.22, remove when the
        # kubernetes-client is upversioned
        webhook_as_list = app_op._kube.list_custom_resources(
            'admissionregistration.k8s.io',
            'v1',
            'validatingwebhookconfigurations',
            label_selector=label_selector
        )

        if len(webhook_as_list) > 1:
            raise exception.LifecycleSemanticCheckException(
                "Multiple Validating Webhook Configurations found for nginx ingress controller"
            )
        if webhook_as_list:
            # FIXME(outbrito): Transparently returning an older version of the object
            api_client = app_op._kube._get_kubernetesclient_admission_registration().api_client
            return api_client._ApiClient__deserialize(webhook_as_list[0], 'V1beta1ValidatingWebhookConfiguration')

    def _delete_webhook_configuration(self, app_op, webhook_name):
        app_op._kube.kube_delete_validating_webhook_configuration(webhook_name)

    def _recreate_webhook_configuration(self, app_op, app):
        webhook = self._get_webhook_configuration(app_op)
        if webhook:
            LOG.info(
                "Validating webhook already present on system. Nothing to be done."
            )
            return

        dbapi_instance = app_op._dbapi
        db_app = dbapi_instance.kube_app_get(app.name)

        user_overrides = self._get_helm_user_overrides(
            dbapi_instance,
            db_app,
            app_constants.HELM_CHART_INGRESS_NGINX,
            app_constants.HELM_NS_NGINX_INGRESS_CONTROLLER,
        )

        if REAPPLY_ADMISSION_WEBHOOK_OVERRIDE not in user_overrides:
            LOG.info("Override for admission webhook not found. Nothing to be done.")
            return

        original_overrides = user_overrides.replace(
            DISABLE_ADMISSION_WEBHOOK_OVERRIDE_CREATION, ""
        ).replace(REAPPLY_ADMISSION_WEBHOOK_OVERRIDE, "")

        updated_overrides = CREATE_ADMISSION_WEBHOOK_OVERRIDE + ": %s\n" % time() + original_overrides

        self._update_helm_user_overrides(
            dbapi_instance,
            db_app,
            app_constants.HELM_CHART_INGRESS_NGINX,
            app_constants.HELM_NS_NGINX_INGRESS_CONTROLLER,
            updated_overrides,
        )

        # Reapply the application to ensure the validating webhook is recreated
        lifecycle_hook_info = LifecycleHookInfo()
        lifecycle_hook_info.operation = constants.APP_APPLY_OP
        app_op.perform_app_apply(
            app._kube_app, LifecycleConstants.APP_LIFECYCLE_MODE_AUTO, lifecycle_hook_info
        )

        if BACKUP_ADMISSION_WEBHOOK_OVERRIDE in original_overrides:
            original_overrides = original_overrides.replace(
                BACKUP_ADMISSION_WEBHOOK_OVERRIDE,
                CREATE_ADMISSION_WEBHOOK_OVERRIDE,
            )

        self._update_helm_user_overrides(
            dbapi_instance,
            db_app,
            app_constants.HELM_CHART_INGRESS_NGINX,
            app_constants.HELM_NS_NGINX_INGRESS_CONTROLLER,
            original_overrides,
        )

    def _get_helm_user_overrides(self, dbapi_instance, app, chart, namespace):
        try:
            return dbapi_instance.helm_override_get(
                app_id=app.id,
                name=chart,
                namespace=namespace,
            ).user_overrides or ""
        except exception.HelmOverrideNotFound:
            # Override for this chart not found, nothing to be done
            return ""

    def _update_helm_user_overrides(self, dbapi_instance, app, chart, namespace, overrides):
        values = {'user_overrides': overrides}
        dbapi_instance.helm_override_update(
            app_id=app.id, name=chart, namespace=namespace, values=values)
