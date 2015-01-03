#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
"""
Programa User Agent Client para comunicación SIP
"""

from xml.sax import make_parser
import socket
import sys
import time
import uaserver


#--------------------------------- Métodos ------------------------------------
def log_debug(oper, ip, port, msg):
    """
    Método para imprimir log en fichero de texto y debug por pantalla
    """
    formatTime = time.strftime('%Y%m%d%H%M%S', time.gmtime(time.time()))
    msgLine = msg.replace("\r\n", " ")
    info = ''
    if oper == 'send':
        info = "Send to " + str(ip) + ':' + str(port) + ': '
        print info + '\n' + msg
    elif oper == 'receive':
        info = "Received from " + str(ip) + ':' + str(port) + ': '
        print info + '\n' + msg
    else:
        print formatTime + ' ' + msg
    logFile = open(LOG_FILE, 'a')
    logFile.write(formatTime + ' ' + info + msgLine + '\n')
    logFile.close()

def send(my_socket, request, servIP, servPort):
    """
    Método para enviar solicitur a un servidor
    """
    # Creamos el socket, lo configuramos y lo atamos al servidor/puerto
    my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    my_socket.connect((servIP, servPort))
    # Enviamos solicitud
    my_socket.send(request)
    log_debug('send', servIP, servPort, request)

def receive(my_socket, servIP, servPort):
    """
    Método para recibir respuesta de un servidor
    """
    # Recibimos respuesta
    try:
        response = my_socket.recv(1024)
    except socket.error:
        error_msg = "Error: No server listening at " + servIP  + " port " \
                  + str(servPort)
        log_debug('', '', '', error_msg)
        raise SystemExit
    log_debug('receive', servIP, servPort, response)
    return response

#-----------------------------Programa principal-------------------------------
# Versión del protocolo SIP
VERSION = "SIP/2.0"

# Parámetros del usuario
if len(sys.argv) != 4:
    sys.exit("Usage: python uaclient.py config method option")
else:
    CONFIG = sys.argv[1]
    method = sys.argv[2].upper()
    OPTION = sys.argv[3]

# Parseo del fichero XML    
parser = make_parser()
dataHandler = uaserver.DataHandler()
parser.setContentHandler(dataHandler)
parser.parse(open(CONFIG))

# Lectura del archivo de configuración UA
attr_dicc = dataHandler.get_attrs()
MY_USERNAME = attr_dicc['userName']
MY_USERPASS = attr_dicc['userPass']
MY_SERVIP = attr_dicc['servIp']
MY_SERVPORT = int(attr_dicc['servPort'])
RTP_PORT = int(attr_dicc['rtpPort'])
PROX_IP = attr_dicc['proxIp']
PROX_PORT = int(attr_dicc['proxPort'])
LOG_FILE = attr_dicc['logPath']
AUDIO_FILE = attr_dicc['audioPath']

# Dirección SIP
MY_ADDRESS = MY_USERNAME + '@dominio.net'

# Comenzando el programa...
log_debug('', '', '', 'Starting...')

#--------------------------------- REGISTER -----------------------------------
if method == 'REGISTER':

    # Enviamos solicitud y recibimos respuesta
    request = method + ' sip:' + MY_ADDRESS + ':' + str(MY_SERVPORT) + ' ' + VERSION + '\r\n'\
            + 'Expires: ' + OPTION + '\r\n\r\n'
    my_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    send(my_socket, request, PROX_IP, PROX_PORT)
    response = receive(my_socket, PROX_IP, PROX_PORT)
    my_socket.close()

#--------------------------------- INVITE -----------------------------------
if method == 'INVITE':

    # Enviamos solicitud y recibimos respuesta
    request = method + ' sip:' + OPTION + ' ' + VERSION + '\r\n' \
            + 'Content-Type: application/sdp\r\n\r\n' + 'v=0\r\n' +  'o=' \
            + MY_ADDRESS + ' ' + MY_SERVIP + '\r\n' + 's=sesion_sip\r\n' \
            + 't=0\r\n' + 'm=audio ' + str(RTP_PORT) + ' RTP'
    my_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    send(my_socket, request, PROX_IP, PROX_PORT)
    response = receive(my_socket, PROX_IP, PROX_PORT)
    my_socket.close()

    # Si recibimos confirmación de INVITE envíamos ACK y recibimos contenido        # ESTO VA AL UASERVER ?????
    response1 = "SIP/1.0 100 Trying\r\n\r\n" + "SIP/1.0 180 Ringing\r\n\r\n"\
              + "SIP/1.0 200 OK\r\n\r\n"
    response2 = "SIP/2.0 100 Trying\r\n\r\n" + "SIP/2.0 180 Ringing\r\n\r\n"\
              + "SIP/2.0 200 OK\r\n\r\n"
    if response == response1 or response == response2:
        method = 'ACK'
        request = method + ' sip:' + OPTION + ' ' + VERSION + '\r\n\r\n'
        my_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        send(my_socket, request, PROX_IP, PROX_PORT)
        response = receive(my_socket, PROX_IP, PROX_PORT)
        my_socket.close()

# Finalizamos programa
log_debug('', '', '', 'Finishing.')
