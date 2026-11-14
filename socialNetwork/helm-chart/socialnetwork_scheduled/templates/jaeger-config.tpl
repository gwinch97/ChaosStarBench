{{- define "socialnetwork.templates.other.jaeger-config.yml"  }}
disabled: {{ .Values.jaeger.disabled | default false }}
reporter:
  logSpans: {{ .Values.jaeger.logSpans | default true }}
  localAgentHostPort: "{{ .Values.jaeger.agentHost }}:{{ .Values.jaeger.agentPort }}"
  queueSize: {{ .Values.jaeger.queueSize | default 100 }}
  bufferFlushInterval: {{ .Values.jaeger.bufferFlushInterval | default 10 }}
sampler:
  type: "{{ .Values.jaeger.samplerType | default "const" }}"
  param: {{ .Values.jaeger.samplerParam | default 1 }}
{{- end }}
