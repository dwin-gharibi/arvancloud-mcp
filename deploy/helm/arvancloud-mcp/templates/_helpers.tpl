{{- define "arvancloud-mcp.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "arvancloud-mcp.fullname" -}}
{{- printf "%s-%s" .Release.Name (include "arvancloud-mcp.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "arvancloud-mcp.labels" -}}
app.kubernetes.io/name: {{ include "arvancloud-mcp.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end -}}

{{- define "arvancloud-mcp.selectorLabels" -}}
app.kubernetes.io/name: {{ include "arvancloud-mcp.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "arvancloud-mcp.secretName" -}}
{{- if .Values.existingSecret -}}
{{ .Values.existingSecret }}
{{- else -}}
{{ include "arvancloud-mcp.fullname" . }}
{{- end -}}
{{- end -}}
