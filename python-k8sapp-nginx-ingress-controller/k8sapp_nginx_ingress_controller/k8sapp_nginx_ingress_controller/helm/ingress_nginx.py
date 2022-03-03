#
# Copyright (c) 2022 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
from k8sapp_nginx_ingress_controller.common import constants as app_constants
from oslo_log import log
from sysinv.common import constants
from sysinv.common import exception
from sysinv.helm import base

LOG = log.getLogger(__name__)


class IngressNginxHelm(base.BaseHelm):
    """Class to encapsulate helm operations for nginx"""

    CHART = app_constants.HELM_CHART_INGRESS_NGINX

    SUPPORTED_NAMESPACES = base.BaseHelm.SUPPORTED_NAMESPACES + \
        [app_constants.HELM_NS_NGINX_INGRESS_CONTROLLER]

    SUPPORTED_APP_NAMESPACES = {
        constants.HELM_APP_NGINX_IC:
            base.BaseHelm.SUPPORTED_NAMESPACES +
            [app_constants.HELM_NS_NGINX_INGRESS_CONTROLLER]
    }

    def get_overrides(self, namespace=None):
        LOG.info("Generating system_overrides for %s chart." % self.CHART)
        ip_family = "IPv6" if self._is_ipv6_cluster_service() else "IPv4"

        overrides = {
            app_constants.HELM_NS_NGINX_INGRESS_CONTROLLER: {
                'controller': {
                    'service': {
                        'ipFamilies': [
                            ip_family
                        ]
                    }
                }
            }
        }

        if namespace in self.SUPPORTED_NAMESPACES:
            return overrides[namespace]
        elif namespace:
            raise exception.InvalidHelmNamespace(chart=self.CHART,
                                                 namespace=namespace)
        else:
            return overrides
