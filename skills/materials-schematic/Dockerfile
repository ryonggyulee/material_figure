FROM docker.io/mambaorg/micromamba:2.10.0
USER root
COPY environment/linux-64.lock /tmp/materials.lock
RUN micromamba install -y -n base -f /tmp/materials.lock && micromamba clean --all --yes
COPY scripts/prepare.py /opt/materials/scripts/prepare.py
COPY assets/presets.json /opt/materials/assets/presets.json
ENV PATH=/opt/conda/bin:$PATH
WORKDIR /work
ENTRYPOINT []
CMD ["python", "/opt/materials/scripts/prepare.py", "--help"]
