FROM solr:9.7
USER root

ADD --chown=solr:solr https://repo1.maven.org/maven2/org/locationtech/jts/jts-core/1.19.0/jts-core-1.19.0.jar /opt/solr/server/solr-webapp/webapp/WEB-INF/lib/

USER solr
