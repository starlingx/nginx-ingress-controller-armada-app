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
from sysinv.helm import lifecycle_base as base

LOG = logging.getLogger(__name__)


class NginxIngressControllerAppLifecycleOperator(base.AppLifecycleOperator):
    def app_lifecycle_actions(self, context, conductor_obj, app_op, app, hook_info):
        """Perform lifecycle actions for an operation

        :param context: request context
        :param conductor_obj: conductor object
        :param app_op: AppOperator object
        :param app: AppOperator.Application object
        :param hook_info: LifecycleHookInfo object

        """
        # Operation
        if hook_info.lifecycle_type == constants.APP_LIFECYCLE_TYPE_OPERATION:
            if hook_info.operation == constants.APP_ETCD_BACKUP:
                if hook_info.relative_timing == constants.APP_LIFECYCLE_TIMING_PRE:
                    return self.pre_etcd_backup(app_op)

        # Use the default behaviour for other hooks
        super(NginxIngressControllerAppLifecycleOperator, self).app_lifecycle_actions(
            context, conductor_obj, app_op, app, hook_info)

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
