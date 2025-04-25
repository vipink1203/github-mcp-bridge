# Deploying GitHub MCP Server on Amazon EKS

This guide explains how to deploy the GitHub MCP server in an Amazon EKS (Elastic Kubernetes Service) cluster, especially alongside an existing n8n deployment.

## Prerequisites

- An existing Amazon EKS cluster
- kubectl configured to communicate with your EKS cluster
- Helm v3 (optional, for Helm chart deployment)
- A GitHub Personal Access Token with appropriate permissions
- Docker hub or ECR access for storing your Docker image

## Step 1: Build and Push the Docker Image

First, build the Docker image for your GitHub MCP server and push it to a container registry that your EKS cluster can access.

### Using Docker Hub

```bash
# Login to Docker Hub
docker login

# Build the image
docker build -t yourusername/github-mcp:latest .

# Push the image
docker push yourusername/github-mcp:latest
```

### Using Amazon ECR

```bash
# Login to ECR
aws ecr get-login-password --region your-region | docker login --username AWS --password-stdin your-account-id.dkr.ecr.your-region.amazonaws.com

# Create repository if it doesn't exist
aws ecr create-repository --repository-name github-mcp --region your-region

# Build the image
docker build -t your-account-id.dkr.ecr.your-region.amazonaws.com/github-mcp:latest .

# Push the image
docker push your-account-id.dkr.ecr.your-region.amazonaws.com/github-mcp:latest
```

## Step 2: Create Kubernetes Secrets

Create a Kubernetes secret to store your GitHub Personal Access Token securely:

```bash
# Create a namespace for the MCP server (if not using an existing one)
kubectl create namespace mcp-system

# Create a secret for the GitHub token
kubectl create secret generic github-mcp-secrets \
  --from-literal=github-token=your_github_personal_access_token \
  --namespace mcp-system
```

## Step 3: Deploy Using Kubernetes Manifests

Create the following Kubernetes manifests to deploy your GitHub MCP server.

### Create deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: github-mcp
  namespace: mcp-system
  labels:
    app: github-mcp
spec:
  replicas: 1
  selector:
    matchLabels:
      app: github-mcp
  template:
    metadata:
      labels:
        app: github-mcp
    spec:
      containers:
      - name: github-mcp
        image: yourusername/github-mcp:latest  # Replace with your image
        env:
        - name: TRANSPORT
          value: "sse"
        - name: PORT
          value: "8050"
        - name: HOST
          value: "0.0.0.0"
        - name: GITHUB_TOKEN
          valueFrom:
            secretKeyRef:
              name: github-mcp-secrets
              key: github-token
        ports:
        - containerPort: 8050
        resources:
          limits:
            cpu: "1"
            memory: "512Mi"
          requests:
            cpu: "200m"
            memory: "256Mi"
        livenessProbe:
          httpGet:
            path: /health
            port: 8050
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8050
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Create service.yaml

```yaml
apiVersion: v1
kind: Service
metadata:
  name: github-mcp
  namespace: mcp-system
spec:
  selector:
    app: github-mcp
  ports:
  - port: 8050
    targetPort: 8050
  type: ClusterIP
```

### Apply the manifests

```bash
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

## Step 4: Alternative - Deploy Using Helm

If you prefer using Helm for managing Kubernetes deployments, you can create a Helm chart.

### Create a Helm Chart Structure

Create a directory structure for your Helm chart:

```bash
mkdir -p github-mcp-chart/templates
```

### Create Chart.yaml

```yaml
# github-mcp-chart/Chart.yaml
apiVersion: v2
name: github-mcp
description: A Helm chart for GitHub MCP Server on Kubernetes
type: application
version: 0.1.0
appVersion: "1.0.0"
```

### Create values.yaml

```yaml
# github-mcp-chart/values.yaml
replicaCount: 1

image:
  repository: yourusername/github-mcp
  tag: latest
  pullPolicy: Always

service:
  type: ClusterIP
  port: 8050

resources:
  limits:
    cpu: 1
    memory: 512Mi
  requests:
    cpu: 200m
    memory: 256Mi

github:
  existingSecret: github-mcp-secrets
  tokenKey: github-token

transport: sse
```

### Create Templates

Move the Kubernetes manifest files to the templates directory and update them to use Helm templating:

```yaml
# github-mcp-chart/templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Release.Name }}
  labels:
    app: {{ .Release.Name }}
    {{- include "github-mcp.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app: {{ .Release.Name }}
  template:
    metadata:
      labels:
        app: {{ .Release.Name }}
    spec:
      containers:
      - name: {{ .Release.Name }}
        image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
        imagePullPolicy: {{ .Values.image.pullPolicy }}
        env:
        - name: TRANSPORT
          value: {{ .Values.transport | quote }}
        - name: PORT
          value: "{{ .Values.service.port }}"
        - name: HOST
          value: "0.0.0.0"
        - name: GITHUB_TOKEN
          valueFrom:
            secretKeyRef:
              name: {{ .Values.github.existingSecret }}
              key: {{ .Values.github.tokenKey }}
        ports:
        - containerPort: {{ .Values.service.port }}
        resources:
          {{- toYaml .Values.resources | nindent 12 }}
        livenessProbe:
          httpGet:
            path: /health
            port: {{ .Values.service.port }}
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: {{ .Values.service.port }}
          initialDelaySeconds: 5
          periodSeconds: 5
```

```yaml
# github-mcp-chart/templates/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ .Release.Name }}
  labels:
    {{- include "github-mcp.labels" . | nindent 4 }}
spec:
  type: {{ .Values.service.type }}
  ports:
  - port: {{ .Values.service.port }}
    targetPort: {{ .Values.service.port }}
    protocol: TCP
    name: http
  selector:
    app: {{ .Release.Name }}
```

```yaml
# github-mcp-chart/templates/_helpers.tpl
{{/*
Common labels
*/}}
{{- define "github-mcp.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/name: {{ .Release.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}
```

### Install the Helm Chart

```bash
# Create the secret first
kubectl create secret generic github-mcp-secrets \
  --from-literal=github-token=your_github_personal_access_token \
  --namespace mcp-system

# Install the chart
helm install github-mcp ./github-mcp-chart --namespace mcp-system
```

## Step 5: Integrating with n8n in EKS

If you have n8n running in the same EKS cluster, you'll need to configure it to use the GitHub MCP server.

### Install the MCP Community Node in n8n

First, make sure the n8n-nodes-mcp community node is installed in your n8n deployment.

If you're using Helm for n8n, update your values.yaml:

```yaml
n8n:
  extraEnv:
    - name: N8N_COMMUNITY_PACKAGES
      value: "n8n-nodes-mcp"
    - name: N8N_COMMUNITY_PACKAGES_ALLOW_TOOL_USAGE
      value: "true"
```

If not using Helm, update your n8n deployment:

```bash
kubectl edit deployment n8n -n your-n8n-namespace
```

Add these environment variables:

```yaml
env:
- name: N8N_COMMUNITY_PACKAGES
  value: "n8n-nodes-mcp"
- name: N8N_COMMUNITY_PACKAGES_ALLOW_TOOL_USAGE
  value: "true"
```

### Configure n8n to Access the MCP Server

Once n8n is set up with the MCP node, you'll need to configure it to connect to your GitHub MCP server. This is done through the n8n UI:

1. Access your n8n web interface
2. Go to Settings > Credentials > New Credentials
3. Select "MCP Client API"
4. Configure with:
   - Name: GitHub MCP
   - Transport Type: Server-Sent Events (SSE)
   - Server URL: http://github-mcp.mcp-system:8050/sse
   
   Note: The URL follows the format `http://<service-name>.<namespace>:<port>/sse`

5. Save the credentials

## Step 6: Scaling and Production Considerations

For production deployments, consider these enhancements:

### High Availability

Update your deployment to run multiple replicas:

```yaml
spec:
  replicas: 2  # or more depending on your needs
```

### Resource Management

Adjust CPU and memory resources based on load:

```yaml
resources:
  limits:
    cpu: "2"
    memory: "1Gi"
  requests:
    cpu: "500m"
    memory: "512Mi"
```

### Horizontal Pod Autoscaler

Create an HPA to automatically scale based on CPU usage:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: github-mcp-hpa
  namespace: mcp-system
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: github-mcp
  minReplicas: 1
  maxReplicas: 5
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 75
```

### Network Policies

Create a network policy to restrict access to the GitHub MCP server:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: github-mcp-network-policy
  namespace: mcp-system
spec:
  podSelector:
    matchLabels:
      app: github-mcp
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: your-n8n-namespace
    - podSelector:
        matchLabels:
          app: n8n
    ports:
    - protocol: TCP
      port: 8050
```

### Persistent Storage for Logs

Add persistent storage if you need to maintain logs:

```yaml
volumes:
- name: logs
  persistentVolumeClaim:
    claimName: github-mcp-logs
volumeMounts:
- name: logs
  mountPath: /app/logs
```

## Step 7: Monitoring and Maintenance

### Prometheus Monitoring

Add Prometheus annotations to your deployment for metrics collection:

```yaml
template:
  metadata:
    annotations:
      prometheus.io/scrape: "true"
      prometheus.io/path: "/metrics"
      prometheus.io/port: "8050"
```

### Logging

Use AWS CloudWatch for log aggregation:

```yaml
# Install the CloudWatch agent as a sidecar
containers:
- name: cloudwatch-agent
  image: amazon/cloudwatch-agent:latest
  # ... configuration ...
```

## Troubleshooting

### Check Pod Status

```bash
kubectl get pods -n mcp-system
```

### View Logs

```bash
kubectl logs -n mcp-system deployment/github-mcp
```

### Check Service

```bash
kubectl get svc -n mcp-system
```

### Test Connection from n8n Pod

```bash
kubectl exec -it -n your-n8n-namespace deploy/n8n -- curl http://github-mcp.mcp-system:8050/health
```

### Common Issues

1. **Connection refused**: Check if the service and pods are running correctly
2. **Authentication failures**: Verify the GitHub token secret is correctly set
3. **Resource constraints**: Check for resource limits being reached

## Conclusion

You now have a GitHub MCP server deployed in your EKS cluster and integrated with n8n. This setup allows AI agents to interact with GitHub Enterprise data in a structured and secure way.

For ongoing maintenance, keep your GitHub token updated and monitor the server's performance to ensure it meets your needs.
