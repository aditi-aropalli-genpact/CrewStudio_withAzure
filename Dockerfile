# Baseimage
FROM python:3.12.5-slim-bookworm

# Update Packages
RUN apt update
RUN apt upgrade -y
RUN pip install --upgrade pip
# install git
RUN apt-get install build-essential -y

# Copy CrewAI-Studio
RUN mkdir /CrewAI-Studio
COPY ./ /CrewAI-Studio/

# into deer
WORKDIR /CrewAI-Studio
RUN pip install -r requirements.txt

# Run app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EXPOSE 8000