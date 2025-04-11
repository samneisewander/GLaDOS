FROM python:3.12.3-slim

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY ./code /code

WORKDIR /code

CMD ["python", "./GLaDOS.py"]