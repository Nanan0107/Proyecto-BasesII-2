# Entorno de la Etapa 1: JupyterLab + PySpark 3.5 + Apache Sedona (Spark local).
FROM python:3.12-slim-bookworm

ARG SEDONA_VERSION=1.9.1
ARG GEOTOOLS_VERSION=1.9.1-33.5

# Spark 3.5 requiere Java 8/11/17
RUN apt-get update \
 && apt-get install -y --no-install-recommends openjdk-17-jre-headless curl \
 && rm -rf /var/lib/apt/lists/*
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Jars de Sedona dentro de la instalación de PySpark: así no hay descargas de
# Maven/Ivy al iniciar la sesión y el entorno es reproducible sin red.
RUN JARS=$(python -c "import pyspark, os; print(os.path.join(os.path.dirname(pyspark.__file__), 'jars'))") \
 && curl -fsSL -o $JARS/sedona-spark-shaded-3.5_2.12-${SEDONA_VERSION}.jar \
      https://repo1.maven.org/maven2/org/apache/sedona/sedona-spark-shaded-3.5_2.12/${SEDONA_VERSION}/sedona-spark-shaded-3.5_2.12-${SEDONA_VERSION}.jar \
 && curl -fsSL -o $JARS/geotools-wrapper-${GEOTOOLS_VERSION}.jar \
      https://repo1.maven.org/maven2/org/datasyslab/geotools-wrapper/${GEOTOOLS_VERSION}/geotools-wrapper-${GEOTOOLS_VERSION}.jar

# Usuario sin privilegios con el mismo UID/GID del anfitrión: los archivos que
# escribe el notebook en el repositorio montado quedan con el dueño correcto.
# Hadoop exige que el usuario exista en /etc/passwd.
ARG UID=1000
ARG GID=1000
RUN groupadd -g ${GID} etl && useradd -m -u ${UID} -g ${GID} etl
USER etl

WORKDIR /proyecto
EXPOSE 8888 4040
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", \
     "--ServerApp.token=", "--ServerApp.root_dir=/proyecto"]
