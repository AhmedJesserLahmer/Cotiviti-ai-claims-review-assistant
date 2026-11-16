{{/* Chart name, truncated to the 63-char DNS label limit. */}}
{{- define "claims-review.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* Release-scoped base name. */}}
{{- define "claims-review.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/* Name of one component: <fullname>-<component>. */}}
{{- define "claims-review.componentName" -}}
{{- printf "%s-%s" (include "claims-review.fullname" .root) .component | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "claims-review.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
app.kubernetes.io/name: {{ include "claims-review.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: claims-review
{{- end -}}

{{/* Selector labels for a component (stable across upgrades). */}}
{{- define "claims-review.selectorLabels" -}}
app.kubernetes.io/name: {{ include "claims-review.name" .root }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}

{{- define "claims-review.componentLabels" -}}
{{ include "claims-review.labels" .root }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}

{{/* image: <registry>/<repository>:<tag>, tag defaults to global tag then appVersion. */}}
{{- define "claims-review.image" -}}
{{- $registry := .root.Values.global.imageRegistry -}}
{{- $tag := .values.image.tag | default .root.Values.global.imageTag | default .root.Chart.AppVersion -}}
{{- if $registry -}}
{{- printf "%s/%s:%s" $registry .values.image.repository $tag -}}
{{- else -}}
{{- printf "%s:%s" .values.image.repository $tag -}}
{{- end -}}
{{- end -}}

{{/* Name of the Secret holding credentials. */}}
{{- define "claims-review.secretName" -}}
{{- if .Values.secrets.existingSecret -}}
{{- .Values.secrets.existingSecret -}}
{{- else -}}
{{- printf "%s-secrets" (include "claims-review.fullname" .) -}}
{{- end -}}
{{- end -}}

{{- define "claims-review.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "claims-review.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{/* In-cluster URLs between components. */}}
{{- define "claims-review.url" -}}
{{- printf "http://%s:%v" (include "claims-review.componentName" (dict "root" .root "component" .component)) .port -}}
{{- end -}}

{{- define "claims-review.mongoUri" -}}
{{- if .Values.mongodb.enabled -}}
{{- printf "mongodb://%s:27017" (include "claims-review.componentName" (dict "root" . "component" "mongodb")) -}}
{{- else -}}
{{- required "mongodb.externalUri is required when mongodb.enabled=false" .Values.mongodb.externalUri -}}
{{- end -}}
{{- end -}}

{{- define "claims-review.redisUrl" -}}
{{- if .Values.redis.enabled -}}
{{- printf "redis://%s:6379/0" (include "claims-review.componentName" (dict "root" . "component" "redis")) -}}
{{- else -}}
{{- .Values.redis.externalUrl -}}
{{- end -}}
{{- end -}}

{{/* Restricted pod security defaults shared by every workload. */}}
{{- define "claims-review.podSecurityContext" -}}
runAsNonRoot: true
seccompProfile:
  type: RuntimeDefault
{{- end -}}

{{- define "claims-review.containerSecurityContext" -}}
allowPrivilegeEscalation: false
readOnlyRootFilesystem: true
capabilities:
  drop: ["ALL"]
{{- end -}}
