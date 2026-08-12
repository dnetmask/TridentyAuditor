{{- define "tridentyauditor.fullname" -}}
{{- .Release.Name }}-tridentyauditor
{{- end -}}

{{- define "tridentyauditor.labels" -}}
app.kubernetes.io/name: tridentyauditor
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "tridentyauditor.selectorLabels" -}}
app.kubernetes.io/name: tridentyauditor
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
