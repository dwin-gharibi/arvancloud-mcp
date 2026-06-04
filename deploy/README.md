# Deploying the ArvanCloud MCP server

Three ways to deploy, all for the HTTP (`streamable-http`) transport so the
server can run remotely and scale.

## 1. Docker (single instance)

```bash
docker build -t arvancloud-mcp:latest .
docker run --rm -p 8000:8000 -e ARVAN_API_KEY='Apikey ...' \
  -e ARVAN_TRANSPORT=streamable-http -e ARVAN_HOST=0.0.0.0 arvancloud-mcp:latest
# MCP endpoint: http://localhost:8000/mcp
```

To include the IaC validators (terraform, checkov, hadolint, …) in the image:

```bash
docker build --build-arg INSTALL_IAC_TOOLS=true -t arvancloud-mcp:iac .
```

## 2. Kubernetes (scales for many loads)

Plain manifests with an HPA (`deploy/kubernetes`):

```bash
kubectl apply -f deploy/kubernetes/namespace.yaml
kubectl -n arvancloud-mcp create secret generic arvancloud-mcp-secrets \
  --from-literal=ARVAN_API_KEY='Apikey ...'
kubectl apply -k deploy/kubernetes
```

The deployment runs `ARVAN_STATELESS_HTTP=true` + `ARVAN_JSON_RESPONSE=true`, so
replicas are interchangeable behind one Service and the HorizontalPodAutoscaler
(2–10 pods on CPU/memory) can scale it under load.

### Helm

```bash
helm install mcp deploy/helm/arvancloud-mcp \
  --namespace arvancloud-mcp --create-namespace \
  --set secrets.ARVAN_API_KEY='Apikey ...' \
  --set ingress.enabled=true --set ingress.host=mcp.example.com
```

## 3. Terraform (provision an ArvanCloud server that runs the MCP)

Uses ArvanCloud's own Terraform provider to create a server, open the port, and
start the container via cloud-init (`deploy/terraform`):

```bash
cd deploy/terraform
terraform init
terraform apply -var="api_key=Apikey ..." -var="region=ir-thr-c2"
```

> Validate any of these manifests with the server's own IaC tools, e.g.
> `arvan_iac_validate_kubernetes` and `arvan_iac_terraform_validate`.
