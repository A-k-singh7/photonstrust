FROM python:3.12-slim

WORKDIR /app

# Install Rust toolchain for building photonstrust_rs (maturin)
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && curl https://sh.rustup.rs -sSf | sh -s -- -y --default-toolchain stable \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.cargo/bin:${PATH}"

# Copy project files
COPY pyproject.toml .
COPY photonstrust/ ./photonstrust/
COPY photonstrust_rs/ ./photonstrust_rs/
COPY scripts/ ./scripts/
COPY app.py .

# Install Python dependencies
RUN pip install --no-cache-dir \
    maturin \
    numpy \
    pyyaml \
    matplotlib \
    scikit-learn \
    fastapi \
    uvicorn \
    rich \
    streamlit>=1.28 \
    streamlit-agraph \
    streamlit-echarts \
    jax[cpu] \
    && pip install --no-cache-dir -e ".[dev,signing]"

# Build and install the Rust extension
RUN cd photonstrust_rs && maturin develop --release

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", \
    "--server.port=8501", \
    "--server.address=0.0.0.0", \
    "--server.headless=true", \
    "--browser.gatherUsageStats=false"]
