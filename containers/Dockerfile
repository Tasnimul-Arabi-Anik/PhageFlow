FROM condaforge/mambaforge:24.3.0-0

COPY envs/phageflow-core.yml /tmp/phageflow-core.yml
RUN mamba env create -f /tmp/phageflow-core.yml && \
    mamba clean -afy

ENV PATH=/opt/conda/envs/phageflow-core/bin:$PATH
ENV CONDA_DEFAULT_ENV=phageflow-core

WORKDIR /work

