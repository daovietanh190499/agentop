FROM alpine/k8s:1.33.0

WORKDIR /

RUN python -m venv venv

RUN venv/bin/pip install gradio

WORKDIR /workspace

COPY --chmod=755 . .

ENTRYPOINT ["/venv/bin/python", "gradio-ui.py"]
