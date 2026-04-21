#
# Copyright (c) 2022-2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
from k8sapp_nginx_ingress_controller.common import constants as app_constants
from oslo_log import log
from sysinv.common import constants
from sysinv.common import exception
from sysinv.helm import base

LOG = log.getLogger(__name__)

IANA_TO_OPENSSL_CIPHER_MAP = {
    'TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384':
        'ECDHE-RSA-AES256-GCM-SHA384',
    'TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256':
        'ECDHE-RSA-AES128-GCM-SHA256',
    'TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384':
        'ECDHE-ECDSA-AES256-GCM-SHA384',
    'TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256':
        'ECDHE-ECDSA-AES128-GCM-SHA256',
    'TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256':
        'ECDHE-RSA-CHACHA20-POLY1305',
    'TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256':
        'ECDHE-ECDSA-CHACHA20-POLY1305',
}


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

    def _get_tls_config(self):
        """Get TLS ssl-protocols and ssl-ciphers from service parameters."""
        tls_min_version = \
            constants.SERVICE_PARAM_PLATFORM_TLS_MIN_VERSION_DEFAULT
        tls_cipher_suite = \
            constants.SERVICE_PARAM_PLATFORM_TLS_CIPHER_SUITE_DEFAULT

        try:
            parms = self.dbapi.service_parameter_get_all(
                service=constants.SERVICE_TYPE_PLATFORM,
                section=constants.SERVICE_PARAM_SECTION_PLATFORM_CONFIG)
            for p in parms:
                if p.name == \
                        constants.SERVICE_PARAM_NAME_PLATFORM_TLS_MIN_VERSION:
                    tls_min_version = p.value
                elif p.name == \
                        constants.SERVICE_PARAM_NAME_PLATFORM_TLS_CIPHER_SUITE:
                    tls_cipher_suite = p.value
        except Exception:
            LOG.warning("Failed to read TLS service parameters, "
                        "using defaults for nginx-ingress overrides")

        if tls_min_version == \
                constants.SERVICE_PARAM_PLATFORM_TLS_VERSION_TLS13:
            ssl_protocols = 'TLSv1.3'
        else:
            ssl_protocols = 'TLSv1.2 TLSv1.3'

        openssl_ciphers = []
        for iana_name in tls_cipher_suite.split(','):
            iana_name = iana_name.strip()
            if not iana_name:
                continue
            openssl_name = IANA_TO_OPENSSL_CIPHER_MAP.get(
                iana_name, iana_name)
            openssl_ciphers.append(openssl_name)

        return ssl_protocols, ':'.join(openssl_ciphers)

    def get_overrides(self, namespace=None):
        LOG.info("Generating system_overrides for %s chart." % self.CHART)

        ssl_protocols, ssl_ciphers = self._get_tls_config()

        overrides = {
            app_constants.HELM_NS_NGINX_INGRESS_CONTROLLER: {
                'controller': {
                    'config': {
                        'ssl-protocols': ssl_protocols,
                        'ssl-ciphers': ssl_ciphers,
                    },
                    'service': {
                        'ipFamilyPolicy': 'PreferDualStack',
                        'ipFamilies': []
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
