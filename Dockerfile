FROM registry.access.redhat.com/ubi8/ubi-minimal

ADD secrets_broker/*.txt /secrets_broker/

RUN microdnf install python3 sqlite shadow-utils && microdnf clean all && \
    pip3 install -r /secrets_broker/requirements.txt && \
    rm -rf /root/.cache

# apscheduler fix
RUN echo "UTC" > /etc/timezone

RUN adduser --gid 0 -d /secrets_broker --no-create-home -c 'Secrets broker user' sbu

ADD secrets_broker/*.py /secrets_broker/
ADD secrets_broker/*.yml /secrets_broker/

USER sbu

EXPOSE 8000

CMD python3 -m secrets_broker.secrets_broker
