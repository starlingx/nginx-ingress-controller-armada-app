#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
"""Tests for common constants module."""

import unittest

from k8sapp_nginx_ingress_controller.common \
    import constants as app_constants
from sysinv.helm import common


class TestConstants(unittest.TestCase):
    """Test constants values."""

    def test_helm_ns(self):
        """Test HELM_NS matches kube-system."""
        self.assertEqual(
            app_constants
            .HELM_NS_NGINX_INGRESS_CONTROLLER,
            common.HELM_NS_KUBE_SYSTEM
        )

    def test_helm_chart_ingress_nginx(self):
        """Test HELM_CHART_INGRESS_NGINX value."""
        self.assertEqual(
            app_constants.HELM_CHART_INGRESS_NGINX,
            'ks-ingress-nginx'
        )

    def test_helm_chart_legacy(self):
        """Test HELM_CHART_LEGACY_INGRESS_NGINX."""
        self.assertEqual(
            app_constants
            .HELM_CHART_LEGACY_INGRESS_NGINX,
            'nginx-ingress'
        )

    def test_chart_group(self):
        """Test CHART_GROUP_INGRESS_NGINX value."""
        self.assertEqual(
            app_constants.CHART_GROUP_INGRESS_NGINX,
            'nginx-ingress'
        )
