# Application tunables (maps to metadata)
%global app_name nginx-ingress-controller
%global helm_repo stx-platform
%global armada_nginx_version 0.41.2
%global fluxcd_nginx_version 1.1.1

%global armada_folder  /usr/lib/armada

# Install location
%global app_folder /usr/local/share/applications/helm

# Build variables
%global helm_folder /usr/lib/helm
%global toolkit_version 0.1.0

Summary: StarlingX Nginx Ingress Controller Application FluxCD Helm Charts
#StarlingX Nginx Ingress Controller Application Armada Helm Charts
Name: stx-nginx-ingress-controller-helm
Version: 1.1
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: Wind River <info@windriver.com>
URL: unknown

Source0: %{name}-%{version}.tar.gz

# fluxcd specific source items
Source1: helm-charts-ingress-nginx-%{fluxcd_nginx_version}.tar.gz

BuildArch: noarch

Patch01: 0001-add-toleration-fluxcd.patch

BuildRequires: helm
BuildRequires: chartmuseum
BuildRequires: python-k8sapp-nginx-ingress-controller
BuildRequires: python-k8sapp-nginx-ingress-controller-wheels

%description
StarlingX Nginx Ingress Controller Application FluxCD Helm Charts

%prep
%setup
# set up fluxcd tar source
cd %{_builddir}
/usr/bin/tar xfv %{SOURCE1}
cd helm-charts
%patch01 -p1

%build
# Host a server for the charts
cd %{_builddir}/helm-charts
chartmuseum --debug --port=8879 --context-path='/charts' --storage="local" --storage-local-rootdir="." &
sleep 2
helm repo add local http://localhost:8879/charts

# Create the tgz file for armada
cd %{_builddir}/stx-nginx-ingress-controller-helm-%{version}
cp files/Makefile %{_builddir}/helm-charts/charts
cd %{_builddir}/helm-charts/charts
make ingress-nginx

# Terminate helm server (the last backgrounded task)
kill %1

# Create a chart tarball compliant with sysinv kube-app.py
%define app_staging %{_builddir}/staging
%define app_tarball_fluxcd %{app_name}-%{version}-%{tis_patch_ver}.tgz

# Setup staging
mkdir -p %{app_staging}
cd %{_builddir}/stx-nginx-ingress-controller-helm-%{version}
cp files/metadata.yaml %{app_staging}
cp -Rv fluxcd-manifests %{app_staging}/
mkdir -p %{app_staging}/charts

cd %{_builddir}/helm-charts
cp charts/*.tgz %{app_staging}/charts
cd %{app_staging}

# Populate metadata
sed -i 's/@APP_NAME@/%{app_name}/g' %{app_staging}/metadata.yaml
sed -i 's/@APP_VERSION@/%{version}-%{tis_patch_ver}/g' %{app_staging}/metadata.yaml
sed -i 's/@HELM_REPO@/%{helm_repo}/g' %{app_staging}/metadata.yaml

# Copy the plugins: installed in the buildroot
mkdir -p %{app_staging}/plugins
cp /plugins/%{app_name}/*.whl %{app_staging}/plugins

find . -type f ! -name '*.md5' -print0 | xargs -0 md5sum > checksum.md5
tar -zcf %{_builddir}/%{app_tarball_fluxcd} -C %{app_staging}/ .

# Cleanup staging
rm -fr %{app_staging}

%install
install -d -m 755 %{buildroot}/%{app_folder}
install -p -D -m 755 %{_builddir}/%{app_tarball_fluxcd} %{buildroot}/%{app_folder}

%files
%defattr(-,root,root,-)
%{app_folder}/%{app_tarball_fluxcd}
