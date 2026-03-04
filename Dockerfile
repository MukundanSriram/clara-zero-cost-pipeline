FROM n8nio/n8n:1.71.0

USER root
RUN apk add --no-cache python3 py3-pip
USER node