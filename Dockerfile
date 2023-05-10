FROM python:3.11.3-alpine3.16@sha256:9efc6e155f287eb424ede74aeff198be75ae04504b1e42e87ec9f221e7410f2d

RUN apk add --update --no-cache --virtual .build-deps \
        build-base \
    && pip install --no-cache-dir \
        python-Levenshtein \
    && apk del --purge .build-deps

COPY ./app.py /app.py
ENTRYPOINT [ "python", "-u", "app.py" ]
