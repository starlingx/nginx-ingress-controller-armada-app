#
# Copyright (c) 2022 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
# All Rights Reserved.
#

""" System inventory Armada manifest operator."""

from k8sapp_nginx_ingress_controller.common import constants as app_constants
from k8sapp_nginx_ingress_controller.helm.ingress_nginx import IngressNginxHelm

from sysinv.common import constants
from sysinv.helm import manifest_base as base


class IngressNginxArmadaManifestOperator(base.ArmadaManifestOperator):
    APP = constants.HELM_APP_NGINX_IC
    ARMADA_MANIFEST = 'operator-manifest'

    CHART_GROUP = app_constants.CHART_GROUP_INGRESS_NGINX
    CHART_GROUPS_LUT = {
        IngressNginxHelm.CHART: CHART_GROUP
    }

    CHARTS_LUT = {
        IngressNginxHelm.CHART: app_constants.HELM_CHART_INGRESS_NGINX
    }

    def platform_mode_manifest_updates(self, dbapi, mode):
        """Update the application manifest based on the platform

        :param dbapi: DB api object
        :param mode: mode to control how to apply the application manifest
        """
        pass
