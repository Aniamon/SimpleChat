FROM python:latest
WORKDIR /app
COPY . .
RUN pip3 install poetry
RUN poetry install
CMD ["poetry", "run", "python", "simplechat/main.py"]
EXPOSE 8080
