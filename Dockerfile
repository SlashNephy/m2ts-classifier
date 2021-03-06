FROM python:alpine

RUN apk add --update --no-cache --virtual .build-deps \
        build-base \
    && pip install --no-cache-dir \
        python-Levenshtein \
    && apk del --purge .build-deps

COPY ./app.py /app.py
ENTRYPOINT [ "python", "-u", "app.py" ]
