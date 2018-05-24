FROM alpine:3.7

EXPOSE 80

RUN apk add --update --no-cache \
      lighttpd \
      git

COPY lighttpd.conf /etc/lighttpd/lighttpd.conf
COPY convert-modules-to-repos /

COPY modules/ /modules/
RUN /convert-modules-to-repos /modules /git

CMD [ "/usr/sbin/lighttpd", "-f", "/etc/lighttpd/lighttpd.conf", "-D" ]
