# nginx stable on trixie, the same Debian release the bench image pins. Digest, not tag: `latest`
# is rebuilt under an operator with no commit here, so two hosts on the same fm version could run
# different nginx bytes. The digest is an OCI index (amd64 + arm64), which bake-images needs.
FROM nginx:1.30.6-trixie@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703 AS base

RUN apt update && DEBIAN_FONTEND=noninteractive apt install -y --no-install-recommends wait-for-it gosu python3 python3-pip && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -U jinja2-cli --break-system-packages

COPY template.conf /config/
COPY 502.html /config/templates/502.html
COPY ./entrypoint.sh /
RUN chmod +x /entrypoint.sh
RUN mkdir -p /etc/nginx/custom && rm -rf /etc/nginx/conf.d/default.conf

ENTRYPOINT ["/bin/bash","/entrypoint.sh"]

# --- app-assets: bundles the baked bench's built frontend assets so the
# app-nginx image serves /assets in image mode. The build context for this
# target is the provisioned frappe-bench tree (see BakeManager.bake), so the
# base-stage COPYs (template.conf/502.html/entrypoint.sh) are staged there too.
# Assets land at nginx's configured root (/workspace/frappe-bench/sites, see
# template.conf `root`), NOT /usr/share/nginx/html.
FROM base AS app-assets
COPY sites/assets /workspace/frappe-bench/sites/assets
