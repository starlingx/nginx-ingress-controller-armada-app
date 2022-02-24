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

Summary: StarlingX Nginx Ingress Controller Application Armada Helm Charts
Name: stx-nginx-ingress-controller-helm
Version: 1.1
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: Wind River <info@windriver.com>
URL: unknown

Source0: helm-charts-ingress-nginx-%{armada_nginx_version}.tar.gz
Source1: repositories.yaml
Source2: index.yaml
Source3: Makefile
Source4: metadata.yaml

# armada specific source items
Source5: nginx_ingress_controller_manifest.yaml

# fluxcd specific source items
Source6: helm-charts-ingress-nginx-%{fluxcd_nginx_version}.tar.gz
Source7: kustomization.yaml
Source8: base_helmrepository.yaml
Source9: base_kustomization.yaml
Source10: base_namespace.yaml
Source11: nginx-ingress_helmrelease.yaml
Source12: nginx-ingress_kustomization.yaml
Source13: nginx-ingress_nginx-ingress-static-overrides.yaml
Source14: nginx-ingress_nginx-ingress-system-overrides.yaml

BuildArch: noarch

Patch01: 0001-add-toleration-armada.patch
Patch02: 0001-add-toleration-fluxcd.patch

BuildRequires: helm
BuildRequires: chartmuseum
BuildRequires: python-k8sapp-nginx-ingress-controller
BuildRequires: python-k8sapp-nginx-ingress-controller-wheels

%description
StarlingX Nginx Ingress Controller Application Armada Helm Charts

%package fluxcd
Summary: StarlingX Nginx Ingress Controller Application FluxCD Helm Charts
Group: base
License: Apache-2.0

%description fluxcd
StarlingX Nginx Ingress Controller Application FluxCD Helm Charts

%prep
%setup -n helm-charts
%patch01 -p1

# set up fluxcd tar source
cd %{_builddir}
rm -rf fluxcd
/usr/bin/mkdir -p fluxcd
cd fluxcd
/usr/bin/tar xfv /builddir/build/SOURCES/helm-charts-ingress-nginx-%{fluxcd_nginx_version}.tar.gz
cd %{_builddir}/fluxcd/helm-charts
%patch02 -p1

%build
# Host a server for the charts
cd %{_builddir}/helm-charts
chartmuseum --debug --port=8879 --context-path='/charts' --storage="local" --storage-local-rootdir="." &
sleep 2
helm repo add local http://localhost:8879/charts

# Create the tgz file for armada
cp %{SOURCE3} charts
cd charts
make ingress-nginx

# Create the tgz file for fluxcd
cd %{_builddir}/fluxcd/helm-charts
cp %{SOURCE3} charts
cd charts
make ingress-nginx

# Terminate helm server (the last backgrounded task)
kill %1

# Create a chart tarball compliant with sysinv kube-app.py
%define app_staging %{_builddir}/staging
%define app_tarball_armada %{app_name}-%{version}-%{tis_patch_ver}.tgz
%define app_tarball_fluxcd %{app_name}-fluxcd-%{version}-%{tis_patch_ver}.tgz

# Setup staging
mkdir -p %{app_staging}
cp %{SOURCE4} %{app_staging}
cp %{SOURCE5} %{app_staging}
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

# package armada
find . -type f ! -name '*.md5' -print0 | xargs -0 md5sum > checksum.md5
tar -zcf %{_builddir}/%{app_tarball_armada} -C %{app_staging}/ .

# package fluxcd
rm -f %{app_staging}/nginx_ingress_controller_manifest.yaml
rm -f %{app_staging}/charts/*.tgz
rm -f %{SOURCE6}
cp %{_builddir}/fluxcd/helm-charts/charts/*.tgz %{app_staging}/charts
fluxcd_dest=%{app_staging}/fluxcd-manifests
mkdir -p $fluxcd_dest
cp %{SOURCE7} %{app_staging}/fluxcd-manifests
cd %{_sourcedir}
directories="base nginx-ingress"
for dir in $directories;
do
  mkdir -p $dir
  prefix="${dir}_"
  for file in ${dir}_*; do
    mv $file $dir/"${file#$prefix}"
  done
  cp -r $dir $fluxcd_dest
done
cd -

find . -type f ! -name '*.md5' -print0 | xargs -0 md5sum > checksum.md5
tar -zcf %{_builddir}/%{app_tarball_fluxcd} -C %{app_staging}/ .

# Cleanup staging
rm -fr %{app_staging}

%install
install -d -m 755 %{buildroot}/%{app_folder}
install -p -D -m 755 %{_builddir}/%{app_tarball_armada} %{buildroot}/%{app_folder}
install -p -D -m 755 %{_builddir}/%{app_tarball_fluxcd} %{buildroot}/%{app_folder}

%files
%defattr(-,root,root,-)
%{app_folder}/%{app_tarball_armada}

%files fluxcd
%defattr(-,root,root,-)
%{app_folder}/%{app_tarball_fluxcd}
