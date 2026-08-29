#!/bin/sh
set -eu

python -c "import socket; connection=socket.create_connection(('127.0.0.1',3310),3); connection.sendall(b'zPING\\0'); response=connection.recv(16); connection.close(); assert response == b'PONG\\0', response"
