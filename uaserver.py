#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
"""
Clase (y programa principal) para un User Agent Server en SIP
"""

from xml.sax import make_parser
from xml.sax.handler import ContentHandler
import SocketServer
import sys
import os
import time


# Variables globales
MY_ADDRESS = ''
MY_SERVIP = ''
RTP_PORT = ''
uaorig_tuple = ()

#--------------------------------- Clases -------------------------------------
class EchoHandler(SocketServer.DatagramRequestHandler):
    """
    Echo server class
    """

    def handle(self):
        """
        Método para recibir en el manejador y establecer comunicación SIP
        """
        # IP y puerto del cliente (de tupla client_address)
        self.clientIP = str(self.client_address[0])
        self.clientPort = str(self.client_address[1])

        # Inicializando variables SDP
        self.orig_address = ''
        self.media_type = ''

        while 1:
            # Leyendo línea a línea lo que nos envía el cliente
            self.request = self.rfile.read()

            # Si no hay más líneas salimos del bucle infinito
            if not self.request:
                break
            else:
                # Evaluación parámetros obligatorios enviados por cliente
                log_debug('receive', self.clientIP, self.clientPort, self.request)
                try:
                    self.request_list = self.request.split()
                    self.method = self.request_list[0]
                    protocol = self.request_list[1].split(':')[0]
                    self.address = self.request_list[1].split(':')[1]
                    user = self.address.split('@')[0]
                    domain = self.address.split('@')[1]
                    client_version = self.request_list[2]

                # Envío de "Bad Request"
                    if protocol != 'sip' or client_version != 'SIP/1.0'\
                        and client_version != 'SIP/2.0':
                        response = MY_VERSION + " 400 Bad Request\r\n\r\n"
                        self.wfile.write(response)
                        log_debug('send', self.clientIP, self.clientPort, response)
                        break
                except:
                    response = MY_VERSION + " 400 Bad Request\r\n\r\n"
                    self.wfile.write(response)
                    log_debug('send', self.clientIP, self.clientPort, response)
                    break

                # Evaluación del método SIP recibido
                self.checkmethod()

    def checkmethod(self):
        """
        Método para evaluar método SIP recibido
        """
        # ------------------------- INVITE ------------------------------------
        if self.method == 'INVITE':
            # Evaluación de cabecera y cuerpo del mensaje
            try:
                head = self.request[0:71]
                body = self.request[71:]
                head_list = head.split()
                # Evaluación de parámetros SDP
                if head_list[4] == 'application/sdp':
                    sdp_list = body.split()
                    self.orig_address = sdp_list[1].split('=')[1]
                    uaorig_IP = sdp_list[2]
                    self.media_type = sdp_list[5].split('=')[1]
                    uaorig_mediaport = sdp_list[6]
                    global uaorig_tuple
                    uaorig_tuple = (uaorig_IP, uaorig_mediaport)
            # Envío de "Bad Request"
            except:
                response = MY_VERSION + " 400 Bad Request\r\n\r\n"
                self.wfile.write(response)
                log_debug('send', self.clientIP, self.clientPort, response)
                pass
            # Envío de "Trying, Ringing, OK"
            response = MY_VERSION + " 100 Trying\r\n\r\n"\
                     + MY_VERSION + " 180 Ringing\r\n\r\n"\
                     + MY_VERSION + " 200 OK\r\n"\
                     + 'Content-Type: application/sdp\r\n\r\n' + 'v=0\r\n'\
                     + 'o=' + MY_ADDRESS + ' ' + MY_IP + '\r\n'\
                     + 's=sesion_sip\r\n' + 't=0\r\n' + 'm=audio '\
                     + str(RTP_PORT) + ' RTP\r\n'
            self.wfile.write(response)
            log_debug('send', self.clientIP, self.clientPort, response)

        # ---------------------------- ACK ------------------------------------
        elif self.method == 'ACK':
            # --------------------- Envío RTP ---------------------------------
            uaorig_IP = uaorig_tuple[0]
            uaorig_mediaport = uaorig_tuple[1]
            toRun = "./mp32rtp -i " + uaorig_IP + " -p " + uaorig_mediaport + " < " + AUDIO_FILE
            log_debug('send', uaorig_IP, uaorig_mediaport, AUDIO_FILE)
            print "Sending RTP content to client..."
            os.system(toRun)
            print "Finalizado envío RTP"

        # -------------------- Método no permitido ----------------------------
        else:
            # Envío de "Method Not Allowed"
            response = MY_VERSION + " 405 Method Not Allowed\r\n\r\n"
            self.wfile.write(response)
            log_debug('send', self.clientIP, self.clientPort, response)

class DataHandler(ContentHandler):
    """
    Clase DataHandler
    """

    def __init__(self):
        """
        Constructor. Inicializa el diccionario de atributos
        """
        self.attr_dicc = {}

    def startElement(self, name, attrs):
        """
        Método que añade atributos al diccionario
        """
        if name == 'account':
            username = attrs.get('username', "")
            passwd = attrs.get('passwd', "")
            self.attr_dicc['userName'] = username
            self.attr_dicc['userPass'] = passwd

        if name == 'uaserver':
            ip = attrs.get('ip', "")
            puerto = attrs.get('puerto', "")
            self.attr_dicc['servIp'] = ip
            self.attr_dicc['servPort'] = puerto

        if name == 'rtpaudio':
            puerto = attrs.get('puerto', "")
            self.attr_dicc['rtpPort'] = puerto

        if name == 'regproxy':
            ip = attrs.get('ip', "")
            puerto = attrs.get('puerto', "")
            self.attr_dicc['proxIp'] = ip
            self.attr_dicc['proxPort'] = puerto

        if name == 'log':
            path = attrs.get('path', "")
            self.attr_dicc['logPath'] = path

        if name == 'audio':
            path = attrs.get('path', "")
            self.attr_dicc['audioPath'] = path

    def get_attrs(self):
        """
        Método que devuelve lista con atributos
        """
        return self.attr_dicc

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

#-----------------------------Programa principal-------------------------------
if __name__ == "__main__":
    # Versión del protocolo SIP
    MY_VERSION = "SIP/2.0"

    # Evaluación de parámetros de la línea de comandos
    if len(sys.argv) != 2:
        sys.exit("Usage: python uaserver.py config")
    else:
        CONFIG = sys.argv[1]

    # Parseo del fichero XML    
    parser = make_parser()
    dataHandler = DataHandler()
    parser.setContentHandler(dataHandler)
    parser.parse(open(CONFIG))

    # Lectura del archivo de configuración UA
    attr_dicc = dataHandler.get_attrs()
    MY_USERNAME = attr_dicc['userName']
    MY_USERPASS = attr_dicc['userPass']
    MY_IP = attr_dicc['servIp']
    MY_PORT = int(attr_dicc['servPort'])
    RTP_PORT = attr_dicc['rtpPort']
    PROX_IP = attr_dicc['proxIp']
    PROX_PORT = attr_dicc['proxPort']
    LOG_FILE = attr_dicc['logPath']
    AUDIO_FILE = attr_dicc['audioPath']

    # Dirección SIP
    MY_ADDRESS = MY_USERNAME + '@dominio.net'

    # Comenzando el programa...
    log_debug('', '', '', 'Starting...')

    # Creamos servidor de eco y escuchamos
    serv = SocketServer.UDPServer((MY_IP, MY_PORT), EchoHandler)
    print "UA Server listening at " + MY_IP + ':' + str(MY_PORT) + "..."
    serv.serve_forever()
