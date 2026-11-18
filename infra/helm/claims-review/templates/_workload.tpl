{{/*
Deployment + ConfigMap (+ Service when .port is set) for one component.
Arguments (dict):
  root       top-level context
  component  component name (claims-api, ai-agent, ...)
  values     the component's values block
  env        list of extra env entries (secrets, computed URLs)
  command    optional container command override
  probes     "http" (default) | "tcp" | "none"
  volumes / volumeMounts / initContainers   optional extra YAML lists
*/}}
{{- define "claims-review.workload" -}}
{{- $root := .root -}}
{{- $v := .values -}}
{{- $name := include "claims-review.componentName" (dict "root" $root "component" .component) -}}
{{- $probes := .probes | default "http" -}}
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ $name }}
  labels:
    {{- include "claims-review.componentLabels" (dict "root" $root "component" .component) | nindent 4 }}
data:
  SERVICE_NAME: {{ .component | quote }}
  ENVIRONMENT: {{ $root.Values.global.environment | quote }}
  LOG_LEVEL: {{ $root.Values.global.logLevel | quote }}
  LOG_FORMAT: "json"
  PYTHONUNBUFFERED: "1"
  {{- with $root.Values.observability.otlpEndpoint }}
  OTEL_EXPORTER_OTLP_ENDPOINT: {{ . | quote }}
  {{- end }}
  {{- range $key, $value := ($v.env | default dict) }}
  {{ $key }}: {{ $value | quote }}
  {{- end }}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ $name }}
  labels:
    {{- include "claims-review.componentLabels" (dict "root" $root "component" .component) | nindent 4 }}
spec:
  {{- if not (and $v.autoscaling $v.autoscaling.enabled) }}
  replicas: {{ $v.replicas }}
  {{- end }}
  revisionHistoryLimit: 5
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
  selector:
    matchLabels:
      {{- include "claims-review.selectorLabels" (dict "root" $root "component" .component) | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "claims-review.selectorLabels" (dict "root" $root "component" .component) | nindent 8 }}
      annotations:
        # Roll pods when their configuration changes.
        checksum/config: {{ toJson $v.env | sha256sum }}
        checksum/secret: {{ toJson $root.Values.secrets.values | sha256sum | trunc 16 }}
    spec:
      serviceAccountName: {{ include "claims-review.serviceAccountName" $root }}
      automountServiceAccountToken: {{ $root.Values.serviceAccount.automountToken }}
      {{- with $root.Values.global.imagePullSecrets }}
      imagePullSecrets:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      securityContext:
        {{- include "claims-review.podSecurityContext" $root | nindent 8 }}
      terminationGracePeriodSeconds: 40
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              {{- include "claims-review.selectorLabels" (dict "root" $root "component" .component) | nindent 14 }}
      {{- with .initContainers }}
      initContainers:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      containers:
        - name: {{ .component }}
          image: {{ include "claims-review.image" (dict "root" $root "values" $v) }}
          imagePullPolicy: {{ $root.Values.global.imagePullPolicy }}
          {{- with .command }}
          command:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          {{- if .port }}
          ports:
            - name: http
              containerPort: {{ .port }}
              protocol: TCP
          {{- end }}
          envFrom:
            - configMapRef:
                name: {{ $name }}
          {{- with .env }}
          env:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          {{- if eq $probes "http" }}
          startupProbe:
            httpGet: {path: /health/live, port: http}
            periodSeconds: 5
            failureThreshold: 24
          livenessProbe:
            httpGet: {path: /health/live, port: http}
            periodSeconds: 15
            timeoutSeconds: 3
            failureThreshold: 3
          readinessProbe:
            httpGet: {path: /health/ready, port: http}
            periodSeconds: 10
            timeoutSeconds: 3
            failureThreshold: 3
          {{- else if eq $probes "tcp" }}
          livenessProbe:
            tcpSocket: {port: http}
            periodSeconds: 15
          readinessProbe:
            tcpSocket: {port: http}
            periodSeconds: 10
          {{- end }}
          lifecycle:
            # Give load balancers time to drop the pod before it stops accepting traffic.
            preStop:
              exec:
                command: ["sh", "-c", "sleep 5"]
          resources:
            {{- toYaml $v.resources | nindent 12 }}
          securityContext:
            {{- include "claims-review.containerSecurityContext" $root | nindent 12 }}
          volumeMounts:
            - name: tmp
              mountPath: /tmp
            {{- with .volumeMounts }}
            {{- toYaml . | nindent 12 }}
            {{- end }}
      volumes:
        - name: tmp
          emptyDir:
            sizeLimit: 256Mi
        {{- with .volumes }}
        {{- toYaml . | nindent 8 }}
        {{- end }}
{{- if .port }}
---
apiVersion: v1
kind: Service
metadata:
  name: {{ $name }}
  labels:
    {{- include "claims-review.componentLabels" (dict "root" $root "component" .component) | nindent 4 }}
spec:
  type: ClusterIP
  selector:
    {{- include "claims-review.selectorLabels" (dict "root" $root "component" .component) | nindent 4 }}
  ports:
    - name: http
      port: {{ .port }}
      targetPort: http
      protocol: TCP
{{- end }}
{{- end -}}
