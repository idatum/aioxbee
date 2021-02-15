FROM python:3.8

RUN python -m pip install --disable-pip-version-check pyserial_asyncio

# Copy and install python xbee
COPY ./pythonxbee /root/pythonxbee
WORKDIR /root/pythonxbee
RUN python /root/pythonxbee/setup.py install

ADD /app /app
WORKDIR /app

CMD [ "python", "/app/aiozigbee.py"]
