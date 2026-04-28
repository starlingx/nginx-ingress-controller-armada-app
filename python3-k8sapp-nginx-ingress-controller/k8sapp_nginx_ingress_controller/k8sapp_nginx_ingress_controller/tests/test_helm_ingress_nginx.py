#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
"""Tests for IngressNginxHelm chart overrides."""

import mock
import unittest

from k8sapp_nginx_ingress_controller.common \
    import constants as app_constants
from k8sapp_nginx_ingress_controller.helm \
    .ingress_nginx import IngressNginxHelm
from sysinv.common import constants
from sysinv.common import exception


class TestIngressNginxHelm(unittest.TestCase):
    """Tests for IngressNginxHelm class."""

    def setUp(self):
        super(TestIngressNginxHelm, self).setUp()
        self.helm_obj = mock.MagicMock()
        self.instance = IngressNginxHelm(self.helm_obj)

    def test_chart_attribute(self):
        """Test CHART is set to expected constant."""
        self.assertEqual(
            IngressNginxHelm.CHART,
            app_constants.HELM_CHART_INGRESS_NGINX
        )

    def test_supported_namespaces_includes_nginx(self):
        """Test SUPPORTED_NAMESPACES has nginx ns."""
        nginx_ns = (
            app_constants
            .HELM_NS_NGINX_INGRESS_CONTROLLER
        )
        self.assertIn(
            nginx_ns,
            IngressNginxHelm.SUPPORTED_NAMESPACES
        )

    def test_supported_app_namespaces(self):
        """Test SUPPORTED_APP_NAMESPACES for app."""
        app_ns_map = (
            IngressNginxHelm.SUPPORTED_APP_NAMESPACES
        )
        self.assertIn(
            constants.HELM_APP_NGINX_IC,
            app_ns_map
        )
        namespace_list = app_ns_map[
            constants.HELM_APP_NGINX_IC
        ]
        nginx_ns = (
            app_constants
            .HELM_NS_NGINX_INGRESS_CONTROLLER
        )
        self.assertIn(nginx_ns, namespace_list)

    def test_get_overrides_valid_namespace(self):
        """Test get_overrides for valid namespace."""
        nginx_ns = (
            app_constants
            .HELM_NS_NGINX_INGRESS_CONTROLLER
        )
        overrides = self.instance.get_overrides(
            namespace=nginx_ns
        )
        controller = overrides['controller']
        self.assertIn('service', controller)
        self.assertEqual(
            controller['service']['ipFamilyPolicy'],
            'PreferDualStack'
        )
        self.assertEqual(
            overrides['fullnameOverride'],
            'ic-nginx-ingress-ingress-nginx'
        )

    def test_get_overrides_invalid_namespace(self):
        """Test get_overrides raises for invalid ns."""
        self.assertRaises(
            exception.InvalidHelmNamespace,
            self.instance.get_overrides,
            namespace='invalid-namespace'
        )

    def test_get_overrides_no_namespace(self):
        """Test get_overrides with no namespace."""
        overrides = self.instance.get_overrides(
            namespace=None
        )
        nginx_ns = (
            app_constants
            .HELM_NS_NGINX_INGRESS_CONTROLLER
        )
        self.assertIn(nginx_ns, overrides)

    def test_get_overrides_ip_families_empty(self):
        """Test ipFamilies is empty list."""
        nginx_ns = (
            app_constants
            .HELM_NS_NGINX_INGRESS_CONTROLLER
        )
        overrides = self.instance.get_overrides(
            namespace=nginx_ns
        )
        controller = overrides['controller']
        self.assertEqual(
            controller['service']['ipFamilies'],
            []
        )
