#
# Copyright (c) 2022 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
from k8sapp_nginx_ingress_controller.common import constants as app_constants
from oslo_log import log
from sysinv.common import constants
from sysinv.common import exception
from sysinv.common import utils
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

    ADDR_NAME = utils.format_address_name(
        constants.CONTROLLER_HOSTNAME,
        constants.NETWORK_TYPE_OAM)

    def _compute_ip_family_policy(self):
        """
        Compute the IP family policy and list of IP families
        for the service, based on configured address pools.

        Returns a tuple of (policy, ip_families), where:
        - policy is "PreferDualStack" if both IPv4 and
          IPv6 pools are present, otherwise "SingleStack".
        - ip_families is a list of unique families, with the
          primary pool family first in dual-stack scenarios.
        """
        addresses = self.dbapi.address_get_by_name(self.ADDR_NAME)
        family_map = {4: 'IPv4', 6: 'IPv6'}

        # collect unique families
        ip_families = {family_map[addr.family] for addr in addresses}

        # Dual-stack: primary first
        if len(ip_families) > 1:
            networks = self.dbapi.networks_get_by_type(
                constants.NETWORK_TYPE_OAM)
            primary = networks[0].primary_pool_family
            ip_families.discard(primary)
            return "PreferDualStack", [primary] + list(ip_families)

        # Single-stack
        return "SingleStack", list(ip_families)

    def get_overrides(self, namespace=None):
        LOG.info("Generating system_overrides for %s chart." % self.CHART)

        policy, families = self._compute_ip_family_policy()
        overrides = {
            app_constants.HELM_NS_NGINX_INGRESS_CONTROLLER: {
                'controller': {
                    'service': {
                        'ipFamilyPolicy': policy,
                        'ipFamilies': families
                    }
                },
                'fullnameOverride': 'ic-nginx-ingress-ingress-nginx'
            }
        }

        if namespace in self.SUPPORTED_NAMESPACES:
            return overrides[namespace]
        elif namespace:
            raise exception.InvalidHelmNamespace(chart=self.CHART,
                                                 namespace=namespace)
        else:
            return overrides
