FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates curl iputils-ping traceroute whois \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

ARG INSTALL_IAC_TOOLS=false
RUN if [ "$INSTALL_IAC_TOOLS" = "true" ]; then set -eux; \
      apt-get update && apt-get install -y --no-install-recommends unzip git; \
      pip install --no-cache-dir checkov yamllint semgrep; \
      ARCH=amd64; \
      TF=1.9.8; \
      curl -fsSL "https://releases.hashicorp.com/terraform/${TF}/terraform_${TF}_linux_${ARCH}.zip" -o /tmp/tf.zip \
        && unzip /tmp/tf.zip -d /usr/local/bin && rm /tmp/tf.zip; \
      curl -fsSL https://raw.githubusercontent.com/terraform-linters/tflint/master/install_linux.sh | bash; \
      curl -fsSL "https://github.com/yannh/kubeconform/releases/latest/download/kubeconform-linux-${ARCH}.tar.gz" | tar xz -C /usr/local/bin kubeconform; \
      curl -fsSL -o /usr/local/bin/hadolint https://github.com/hadolint/hadolint/releases/latest/download/hadolint-Linux-x86_64 && chmod +x /usr/local/bin/hadolint; \
      curl -fsSL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin; \
      curl -fsSL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin; \
      apt-get clean && rm -rf /var/lib/apt/lists/*; \
    fi

RUN useradd --create-home --uid 10001 appuser
USER appuser

ENV ARVAN_TRANSPORT=streamable-http \
    ARVAN_HOST=0.0.0.0 \
    ARVAN_PORT=8000 \
    ARVAN_STATELESS_HTTP=true \
    ARVAN_JSON_RESPONSE=true

EXPOSE 8000

ENTRYPOINT ["arvancloud-mcp"]
