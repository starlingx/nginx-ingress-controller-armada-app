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

# TLS 1.3 ciphers use IANA names directly and must be configured via
# nginx 'ssl-ciphersuites' (SSL_CTX_set_ciphersuites), not 'ssl-ciphers'
# (SSL_CTX_set_cipher_list) which only accepts TLS 1.2 ciphers.
TLS13_CIPHERS = {
    'TLS_AES_256_GCM_SHA384',
    'TLS_AES_128_GCM_SHA256',
    'TLS_CHACHA20_POLY1305_SHA256',
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
        """Get TLS ssl-protocols, ssl-ciphers, and ssl-ciphersuites."""
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

        tls12_ciphers = []
        tls13_ciphers = []
        for iana_name in tls_cipher_suite.split(','):
            iana_name = iana_name.strip()
            if not iana_name:
                continue
            if iana_name in TLS13_CIPHERS:
                tls13_ciphers.append(iana_name)
            else:
                openssl_name = IANA_TO_OPENSSL_CIPHER_MAP.get(
                    iana_name, iana_name)
                tls12_ciphers.append(openssl_name)

        return (ssl_protocols,
                ':'.join(tls12_ciphers),
                ':'.join(tls13_ciphers))

    def get_overrides(self, namespace=None):
        LOG.info("Generating system_overrides for %s chart." % self.CHART)

        ssl_protocols, ssl_ciphers, ssl_ciphersuites = self._get_tls_config()

        config = {
            'ssl-protocols': ssl_protocols,
        }
        if ssl_ciphers:
            config['ssl-ciphers'] = ssl_ciphers
        if ssl_ciphersuites:
            config['ssl-ciphersuites'] = ssl_ciphersuites

        overrides = {
            app_constants.HELM_NS_NGINX_INGRESS_CONTROLLER: {
                'controller': {
                    'config': config,
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
