#
# Copyright (c) 2021 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
# All Rights Reserved.
#

"""System inventory App lifecycle operator."""

from k8sapp_nginx_ingress_controller.common import constants as app_constants
from oslo_log import log as logging
from sysinv.common import constants
from sysinv.common import exception
from sysinv.db import api as dbapi
from sysinv.helm import lifecycle_base as base
from sysinv.helm import lifecycle_utils

LOG = logging.getLogger(__name__)


class NginxIngressControllerAppLifecycleOperator(base.AppLifecycleOperator):
    def app_lifecycle_actions(self, context, conductor_obj, app_op, app, hook_info):
        """Perform lifecycle actions for an operation

        :param context: request context, can be None
        :param conductor_obj: conductor object, can be None
        :param app_op: AppOperator object
        :param app: AppOperator.Application object
        :param hook_info: LifecycleHookInfo object

        """
        if hook_info.lifecycle_type == constants.APP_LIFECYCLE_TYPE_OPERATION:
            if hook_info.operation == constants.APP_ETCD_BACKUP:
                if hook_info.relative_timing == constants.APP_LIFECYCLE_TIMING_PRE:
                    return self.pre_etcd_backup(app_op)

        if hook_info.lifecycle_type == constants.APP_LIFECYCLE_TYPE_RESOURCE:
            if hook_info.operation == constants.APP_APPLY_OP:
                if hook_info.relative_timing == constants.APP_LIFECYCLE_TIMING_PRE:
                    return self.pre_apply(app_op, app, hook_info)

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

        old_chart_overrides = self._get_helm_overrides(
            dbapi_instance,
            from_db_app,
            app_constants.HELM_CHART_LEGACY_INGRESS_NGINX,
            app_constants.HELM_NS_NGINX_INGRESS_CONTROLLER)

        new_chart_overrides = self._get_helm_overrides(
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
                old_chart_overrides)

    def pre_etcd_backup(self, app_op):
        """Pre Etcd backup actions

        :param app_op: AppOperator object

        """
        LOG.info("Executing pre_etcd_backup for {} app".format(constants.HELM_APP_NGINX_IC))
        label_selector = "app.kubernetes.io/name={}," \
                         "app.kubernetes.io/component={}"\
                         .format(app_constants.HELM_CHART_INGRESS_NGINX, "admission-webhook")
        # pylint: disable=protected-access
        webhooks = app_op._kube.kube_get_validating_webhook_configurations_by_selector(label_selector, "")
        if webhooks:
            admission_webhook = webhooks[0].metadata.name
            # pylint: disable=protected-access
            app_op._kube.kube_delete_validating_webhook_configuration(admission_webhook)

    def _get_helm_overrides(self, dbapi_instance, app, chart, namespace):
        try:
            override = dbapi_instance.helm_override_get(app_id=app.id, name=chart, namespace=namespace)
        except exception.HelmOverrideNotFound:
            # Override for this chart not be found, nothing to be done
            return None

        return override['user_overrides']

    def _update_helm_user_overrides(self, dbapi_instance, app, chart, namespace, overrides):
        values = {'user_overrides': overrides}
        dbapi_instance.helm_override_update(
            app_id=app.id, name=chart, namespace=namespace, values=values)
