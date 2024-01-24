import uuid as ud
import socket
import enum
import json
import os

class ExCode(enum.Enum):
    Success     =   0
    StartFail   =   1
    StopFail    =   2
    BadData     =   3
    BadConn     =   4
    Timeout     =   5

class StartValues(object):
    EnableUnixManager   =   False
    UnixPath            =   'oon.socket'
    UnixIsServer        =   True
    UnixEncoding        =   "utf-8"
    DefaultUnixTimeout  =   None
    UnixQueueSize       =   3
    DefaultUnixBytes    =   1024
    DefaultUnixClient   =   None

    EnableNetManager    =   False
    NetIp               =   '127.0.0.1'
    NetPort             =   9090
    NetIsServer         =   True
    NetEncoding         =   "utf-8"
    DefaultNetTimeout   =   None
    NetQueueSize        =   1
    DefaultNetBytes     =   1024
    DefaultNetClient    =   None

    EnableConvertManager    =   True
    ConvertModules                 =   []
    ConvertClasses                 =   []
    DefaultNetobj           =   None
    DefaultMessageString    =   None
    DefaultIgnoreFields     =   []

    @staticmethod
    def all_fields_info():
        return f"""
Unix named sockets connection settings:
EnableUnixManager : bool = {StartValues.EnableUnixManager} - do you want to transfer data over unix named sockets?
UnixPath : str = {StartValues.UnixPath} - path to unix socket file
UnixIsServer : bool = {StartValues.UnixIsServer} - start in server mode or in client mode
UnixEncoding : str = {StartValues.UnixEncoding} - encoding for messages
DefaultUnixTimeout : int = {StartValues.DefaultUnixTimeout} - timeout for operations with transfering
data (if started in server mode, client sonnections inherit this option)
UnixQueueSize : int = {StartValues.UnixQueueSize} - connections queue
DefaultUnixBytes : int = {StartValues.DefaultUnixBytes} - size of message to expect on receive_data()
DefaultUnixClient : _UnixClient = {StartValues.DefaultUnixClient} - default value where _UnixClient needed

Network connection settings:
EnableNetManager : bool = {StartValues.EnableNetManager} - do you want to transfer data over unix named sockets?
NetIp : str = {StartValues.NetIp} - server ip
NetPort : int = {StartValues.NetPort} - server port
NetIsServer : bool = {StartValues.NetIsServer} - start in server mode or in client mode
NetEncoding : str = {StartValues.NetEncoding} - encoding for messages
DefaultNetTimeout : int = {StartValues.DefaultNetTimeout} - timeout for operations with transfering
data (if started in server mode, client sonnections inherit this option)
NetQueueSize : int = {StartValues.NetQueueSize} - connections queue
DefaultNetBytes : int = {StartValues.DefaultNetBytes} - size of message to expect on receive_data()
DefaultNetClient : _NetClient = {StartValues.DefaultNetClient} - default value where _NetClient needed

Converter settings:
EnableConvertManager : bool = {StartValues.EnableConvertManager} - do not turn this off!
ConvertModules : list = {StartValues.ConvertModules} - list of your custom modules
ConvertClasses : list = {StartValues.ConvertClasses} - list of your custom classes
DefaultNetobj : _NetMessage = {StartValues.DefaultNetobj} - default value where _NetMessage needed
DefaultMessageString : str {StartValues.DefaultMessageString} - default value where _NetMessage needs json_string
DefaultIgnoreFields : list = {StartValues.DefaultIgnoreFields} - default list of fields to ignore
"""


class _ConvertManager(object):
    init    =   False
    classes =   []

    @staticmethod
    def _start_converter(modules : list, classes : list):
        if _ConvertManager.init != False: return ExCode.StartFail
        netobj_list = []
        for mod in modules:
            for objcls in dir(mod):
                if isinstance(getattr(mod, objcls), type):
                    netobj_list.append(getattr(mod, objcls))
        for objcls in classes:
            netobj_list.append(objcls)
        _ConvertManager.classes = netobj_list
        _ConvertManager.init = True
        return ExCode.Success

    @staticmethod
    def _generate_net_message(netobj, fields_to_ignore : list, uuid : str):
        if not _ConvertManager.init: return None, ExCode.StartFail
        new_network_message = _NetMessage(_ConvertManager.classes, netobj, fields_to_ignore, uuid)
        return new_network_message, new_network_message.create_code

    @staticmethod
    def _load_net_message_from_str(messtr : str, fields_to_ignore : list):
        if not _ConvertManager.init: return None, ExCode.StartFail
        old_network_message = _NetMessage(_ConvertManager.classes, messtr, fields_to_ignore)
        return old_network_message, old_network_message.create_code

    @staticmethod
    def _stop(prepare_mod : bool):
        if prepare_mod == True: return ExCode.Success
        _ConvertManager.classes = []
        _ConvertManager.init = False
        return ExCode.Success

    @staticmethod
    def _status():
        return _ConvertManager.init


class _NetClient:
    __slots__ = ['alive', 'socket', 'addr', 'port', 'uuid']
    _count = 0
    def __init__(self, socket, conn : tuple, uuid : str = ud.uuid4().hex[:10]):
        self.socket = socket
        self.addr = conn[0]
        self.port = conn[1]
        self.uuid = uuid
        self.alive = True
        _NetClient._count += 1
    def set_time_out(self, timeout : int):
        try:
            self.socket.settimeout(timeout)
            return ExCode.Success
        except: return ExCode.BadConn
    def __del__(self):
        if self.alive != True: return
        try: self.socket.close()
        except: pass
        _NetClient._count -= 1

class _UnixClient:
    __slots__ = ['alive', 'socket', 'uuid']
    _count = 0
    def __init__(self, socket, uuid : str = ud.uuid4().hex[:10]):
        self.socket = socket
        self.uuid = uuid
        self.alive = True
        _UnixClient._count += 1
    def set_time_out(self, timeout : int):
        try:
            self.socket.settimeout(timeout)
            return ExCode.Success
        except: return ExCode.BadConn
    def __del__(self):
        if self.alive != True: return
        try: self.socket.close()
        except: pass
        _UnixClient._count -= 1


class _UnixManager(object):
    init        =   False
    server_mode =   False
    connected   =   False
    encoding    =   None
    timeout     =   None
    queue_size  =   None
    path        =   None
    unix_socket =   None
    
    @staticmethod
    def _init_connection(is_server : bool, path : str, encoding : str, timeout : int, queue_size : int):
        if _UnixManager.init != False: return ExCode.StartFail
        if is_server == True:
            if _UnixManager._close_unix_socket(path) != ExCode.Success: return ExCode.StartFail
            try:
                _UnixManager.unix_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                _UnixManager.unix_socket.bind(path)
                _UnixManager.unix_socket.listen(queue_size)
                _UnixManager.unix_socket.settimeout(timeout)
            except:
                return ExCode.StartFail
        else:
            try:
                _UnixManager.unix_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                _UnixManager.unix_socket.settimeout(timeout)
            except:
                return ExCode.StartFail
        _UnixManager.server_mode = is_server
        _UnixManager.path = path
        _UnixManager.encoding = encoding
        _UnixManager.timeout = timeout
        _UnixManager.queue_size = queue_size
        _UnixManager.init = True
        return ExCode.Success

#### server methods

    @staticmethod
    def _accept_connection(client_timeout : int):
        if not _UnixManager.init or _UnixManager.server_mode == False: return None, ExCode.StartFail
        try:
            client_conn, client_addr = _UnixManager.unix_socket.accept()
            new_client = _UnixClient(client_conn)
            new_client.set_time_out(client_timeout)
            return new_client, ExCode.Success
        except socket.timeout:
            return None, ExCode.Timeout
        except:
            return None, ExCode.BadConn

    @staticmethod
    def _close_client_connection(client : _UnixClient):
        if not _UnixManager.init or _UnixManager.server_mode == False: return ExCode.StartFail
        if type(client) != _UnixClient: return ExCode.BadConn
        if client.alive != True: return ExCode.BadConn
        try: client.socket.close()
        except: return ExCode.BadConn
        client.alive = False
        _UnixClient._count -= 1
        return ExCode.Success

#### client methods

    @staticmethod
    def _connect_to_srv():
        if not _UnixManager.init or _UnixManager.server_mode == True: return ExCode.StartFail
        if _UnixManager.connected == True: return ExCode.BadConn
        try:
            _UnixManager.unix_socket.connect(_UnixManager.path)
            _UnixManager.connected = True
            return ExCode.Success
        except socket.timeout:
            return ExCode.Timeout
        except:
            return ExCode.BadConn

    @staticmethod
    def _disconnect_from_srv():
        if not _UnixManager.init or _UnixManager.server_mode == True: return ExCode.StartFail
        if _UnixManager.connected == False: return ExCode.BadConn
        try: _UnixManager.unix_socket.close()
        except: return ExCode.BadConn
        _UnixManager.connected = False
        return ExCode.Success

#### shared methods

    @staticmethod
    def _receive_data(client : _UnixClient, bytes : int):
        if not _UnixManager.init: return None, ExCode.StartFail
        if _UnixManager.server_mode == True and client == None: return None, ExCode.BadConn
        elif _UnixManager.server_mode == False and client != None: return None, ExCode.BadConn
        if _UnixManager.server_mode == True and type(client) != _UnixClient: return None, ExCode.BadConn
        if _UnixManager.server_mode == True and client.alive != True: return None, ExCode.BadConn
        if _UnixManager.server_mode == False and _UnixManager.connected == False: return None, ExCode.BadConn
        try:
            if client != None: data = client.socket.recv(bytes)
            else: data = _UnixManager.unix_socket.recv(bytes)
            if not data: return None, ExCode.BadConn
            return data.decode(), ExCode.Success
        except socket.timeout:
            return None, ExCode.Timeout
        except:
            return None, ExCode.BadConn

    @staticmethod
    def _send_data(client : _UnixClient, data : str = "None"):
        if not _UnixManager.init: return ExCode.StartFail
        if _UnixManager.server_mode == True and client == None: return ExCode.BadConn
        elif _UnixManager.server_mode == False and client != None: return ExCode.BadConn
        if _UnixManager.server_mode == True and type(client) != _UnixClient: return ExCode.BadConn
        if _UnixManager.server_mode == True and client.alive != True: return ExCode.BadConn
        if _UnixManager.server_mode == False and _UnixManager.connected == False: return None, ExCode.BadConn
        try:
            if client != None: client.socket.send(data.encode(encoding=_UnixManager.encoding))
            else: _UnixManager.unix_socket.send(data.encode(encoding=_UnixManager.encoding))
            return ExCode.Success
        except socket.timeout:
            return ExCode.Timeout
        except:
            return ExCode.BadConn

    def _close_unix_socket(sock_path : str):
        try:
            os.unlink(sock_path)
            return ExCode.Success
        except Exception as e:
            if os.path.exists(sock_path):
                return ExCode.StopFail
            return ExCode.Success

    @staticmethod
    def _stop(prepare_mod : bool):
        if not _UnixManager.init: ExCode.StopFail
        if _UnixManager.server_mode == True and _UnixClient._count > 0: return ExCode.StopFail
        if prepare_mod == True: return ExCode.Success
        try:
            _UnixManager.unix_socket.close()
            if _UnixManager.server_mode == True: _UnixManager._close_unix_socket(_UnixManager.path)
            _UnixManager.connected = False
            _UnixManager.server_mode = False
            _UnixManager.path = None
            _UnixManager.encoding = None
            _UnixManager.timeout = None
            _UnixManager.queue_size = None
            _UnixManager.init = False
            return ExCode.Success
        except:
            return ExCode.StopFail

    @staticmethod
    def _status():
        return _UnixManager.init

    @staticmethod
    def _connect_status():
        return _UnixManager.connected



class _NetManager(object):
    init        =   False
    server_mode =   False
    connected   =   False
    encoding    =   None
    timeout     =   None
    queue_size  =   None
    ip          =   None
    port        =   None
    net_socket  =   None

    @staticmethod
    def _init_connection(is_server : bool, ip : str, port : int, encoding : str, timeout : int, queue_size : int):
        if _NetManager.init != False: return ExCode.StartFail
        if is_server == True:
            try:
                _NetManager.net_socket = socket.socket()
                _NetManager.net_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                _NetManager.net_socket.bind((ip, port))
                _NetManager.net_socket.listen(queue_size)
                _NetManager.net_socket.settimeout(timeout)
            except:
                return ExCode.StartFail
        else:
            try:
                _NetManager.net_socket = socket.socket()
                _NetManager.net_socket.settimeout(timeout)
            except:
                return ExCode.StartFail
        _NetManager.server_mode = is_server
        _NetManager.ip = ip
        _NetManager.port = port
        _NetManager.encoding = encoding
        _NetManager.timeout = timeout
        _NetManager.queue_size = queue_size
        _NetManager.init = True
        return ExCode.Success

#### server methods

    @staticmethod
    def _accept_connection(client_timeout : int):
        if not _NetManager.init or _NetManager.server_mode == False: return None, ExCode.StartFail
        try:
            client_conn, client_addr = _NetManager.net_socket.accept()
            new_client = _NetClient(client_conn, client_addr)
            new_client.set_time_out(client_timeout)
            return new_client, ExCode.Success
        except socket.timeout:
            return None, ExCode.Timeout
        except:
            return None, ExCode.BadConn

    @staticmethod
    def _close_client_connection(client : _NetClient):
        if not _NetManager.init or _NetManager.server_mode == False: return ExCode.StartFail
        if type(client) != _NetClient: return ExCode.BadConn
        if client.alive != True: return ExCode.BadConn
        try: client.socket.close()
        except: return ExCode.BadConn
        client.alive = False
        _NetClient._count -= 1
        return ExCode.Success

#### client methods

    @staticmethod
    def _connect_to_srv():
        if not _NetManager.init or _NetManager.server_mode == True: return ExCode.StartFail
        if _NetManager.connected == True: return ExCode.BadConn
        try:
            _NetManager.net_socket.connect((_NetManager.ip, _NetManager.port))
            _NetManager.connected = True
            return ExCode.Success
        except socket.timeout:
            return ExCode.Timeout
        except:
            return ExCode.BadConn

    @staticmethod
    def _disconnect_from_srv():
        if not _NetManager.init or _NetManager.server_mode == True: return ExCode.StartFail
        if _NetManager.connected == False: return ExCode.BadConn
        try: _NetManager.net_socket.close()
        except: return ExCode.BadConn
        _NetManager.connected = False
        return ExCode.Success
    
#### shared methods

    @staticmethod
    def _receive_data(client : _NetClient, bytes : int):
        if not _NetManager.init: return None, ExCode.StartFail
        if _NetManager.server_mode == True and client == None: return None, ExCode.BadConn
        elif _NetManager.server_mode == False and client != None: return None, ExCode.BadConn
        if _NetManager.server_mode == True and type(client) != _NetClient: return None, ExCode.BadConn
        if _NetManager.server_mode == True and client.alive != True: return None, ExCode.BadConn
        if _NetManager.server_mode == False and _NetManager.connected == False: return None, ExCode.BadConn
        try:
            if client != None: data = client.socket.recv(bytes)
            else: data = _NetManager.net_socket.recv(bytes)
            if not data: return None, ExCode.BadConn
            return data.decode(), ExCode.Success
        except socket.timeout:
            return None, ExCode.Timeout
        except:
            return None, ExCode.BadConn

    @staticmethod
    def _send_data(client : _NetClient, data : str = "None"):
        if not _NetManager.init: return ExCode.StartFail
        if _NetManager.server_mode == True and client == None: return ExCode.BadConn
        elif _NetManager.server_mode == False and client != None: return ExCode.BadConn
        if _NetManager.server_mode == True and type(client) != _NetClient: return ExCode.BadConn
        if _NetManager.server_mode == True and client.alive != True: return ExCode.BadConn
        if _NetManager.server_mode == False and _NetManager.connected == False: return None, ExCode.BadConn
        try:
            if client != None: client.socket.send(data.encode(encoding=_NetManager.encoding))
            else: _NetManager.net_socket.send(data.encode(encoding=_NetManager.encoding))
            return ExCode.Success
        except socket.timeout:
            return ExCode.Timeout
        except:
            return ExCode.BadConn

    @staticmethod
    def _stop(prepare_mod : bool):
        if not _NetManager.init: ExCode.StopFail
        if _NetManager.server_mode == True and _NetClient._count > 0: return ExCode.StopFail
        if prepare_mod == True: return ExCode.Success
        try:
            _NetManager.net_socket.close()
            _NetManager.connected = False
            _NetManager.server_mode = False
            _NetManager.ip = None
            _NetManager.port = None
            _NetManager.encoding = None
            _NetManager.timeout = None
            _NetManager.queue_size = None
            _NetManager.init = False
            return ExCode.Success
        except:
            return ExCode.StopFail

    @staticmethod
    def _status():
        return _NetManager.init

    @staticmethod
    def _connect_status():
        return _NetManager.connected





class _NetMessage:
    __slots__ = ['create_code', 'json_string', 'netobj', 'uuid']
    def __init__(self, classes : list, body, fields_to_ignore : list, uuid : str = ud.uuid4().hex[:10]):
        final_netobj = None
        final_json_string = json.dumps({"head":{"uuid":uuid}, "body":{}})
        final_uuid = uuid
        final_create_code = ExCode.Success
        if type(body) == str:
            final_json_string = body
            if _NetMessage._check_net_mes_str(final_json_string) != ExCode.Success:
                final_create_code = ExCode.BadData
            else:
                mesdict = json.loads(final_json_string)
                final_uuid = mesdict["head"]["uuid"]
                final_netobj, final_create_code =  _NetMessage._netobj_from_dict(classes, mesdict["body"], fields_to_ignore)
        elif type(body) in classes or body == None:
            final_netobj = body
            objdict, final_create_code = _NetMessage._netobj_to_dict(classes, body, fields_to_ignore)
            mesdict = {"head":{"uuid":uuid}, "body":objdict}
            if _NetMessage._check_net_mes_dict(mesdict) != ExCode.Success:
                final_create_code = ExCode.BadData
            else:
                final_json_string = json.dumps({"head":{"uuid":uuid}, "body":objdict})
        else:
            final_create_code = ExCode.BadData
        self.uuid = final_uuid
        self.json_string = final_json_string
        self.netobj = final_netobj
        self.create_code = final_create_code

    @staticmethod
    def _check_net_mes_str(messtr):
        head_fields = ["uuid"]
        try: mesdict = json.loads(messtr)
        except: return ExCode.BadData
        if type(mesdict) != dict or "head" not in mesdict or "body" not in mesdict: return ExCode.BadData
        for hf in head_fields:
            if hf not in mesdict["head"]: return ExCode.BadData
        return ExCode.Success

    @staticmethod
    def _check_net_mes_dict(mesdict):
        head_fields = ["uuid"]
        if type(mesdict) != dict or "head" not in mesdict or "body" not in mesdict: return ExCode.BadData
        for hf in head_fields:
            if hf not in mesdict["head"]: return ExCode.BadData
        try: json.dumps(mesdict)
        except: return ExCode.BadData
        return ExCode.Success

    @staticmethod
    def _netobj_to_dict(classes, netobj, fields_to_ignore : list):
        if netobj == None: return {}, ExCode.BadData
        if type(netobj) not in classes: return {}, ExCode.BadData
        try: class_attrs = [attr for attr in dir(netobj) if not callable(getattr(netobj, attr)) and not attr.startswith("__")]
        except: return {}, ExCode.BadData
        objdict = {"type":type(netobj).__name__}
        bad_field_types = []
        for field in class_attrs:
            if field in fields_to_ignore: continue
            try: field_value = getattr(netobj, field)
            except: return objdict, ExCode.BadData
            if type(field_value) in bad_field_types: return objdict, ExCode.BadData
            elif isinstance(field_value, enum.Enum):
                if type(field_value) not in classes: return objdict, ExCode.BadData
                objdict[field] = {"type":type(field_value).__name__, "value":field_value.value}
            elif type(field_value) in classes:
                recobjdict, recexcode = _NetMessage._netobj_to_dict(classes, field_value, fields_to_ignore)
                objdict[field] = recobjdict
                if recexcode != ExCode.Success: return objdict, recexcode
            else:
                objdict[field] = field_value
        return objdict, ExCode.Success

    @staticmethod
    def _netobj_from_dict(classes, objdict, fields_to_ignore : list):
        if objdict == {} or type(objdict) != dict or "type" not in objdict: return None, ExCode.BadData
        netobjclass = None
        for objcls in classes:
            if objcls.__name__ == objdict["type"]:
                netobjclass = objcls
                break
        if netobjclass == None: return None, ExCode.BadData
        try:
            if type(netobjclass) == type(enum.Enum):
                return netobjclass(objdict["value"]),  ExCode.Success
            newnetobj = netobjclass()
            class_attrs = [attr for attr in dir(newnetobj) if not callable(getattr(newnetobj, attr)) and not attr.startswith("__")]
        except: return None, ExCode.BadData
        type_field_ignored = False
        for field in objdict:
            if not type_field_ignored:
                type_field_ignored = True
                continue
            if field in fields_to_ignore:
                continue
            elif field not in class_attrs:
                return newnetobj, ExCode.BadData
            elif type(objdict[field]) == dict:
                try:
                    subobj, excode = _NetMessage._netobj_from_dict(classes, objdict[field], fields_to_ignore)
                    setattr(newnetobj, field, subobj)
                    if excode != ExCode.Success: return newnetobj, excode
                except: return newnetobj, ExCode.BadData
            else:
                try: setattr(newnetobj, field, objdict[field])
                except: return newnetobj, ExCode.BadData
        return newnetobj, ExCode.Success




def generate_message(netobj = StartValues.DefaultNetobj, fields_to_ignore : list = StartValues.DefaultIgnoreFields, uuid : str = ud.uuid4().hex[:10]):
    return _ConvertManager._generate_net_message(netobj, fields_to_ignore, uuid)

def load_message_from_str(messtr : str = StartValues.DefaultMessageString, fields_to_ignore : list = StartValues.DefaultIgnoreFields):
    return _ConvertManager._load_net_message_from_str(messtr, fields_to_ignore)

def is_running():
    return {"_UnixManager" : _UnixManager._status(), "_NetManager" : _NetManager._status(), "_ConvertManager" : _ConvertManager._status()}

def is_connected_over_net():
    return _NetManager._connect_status()

def is_connected_over_unix():
    return _UnixManager._connect_status()

def start():
    start_codes = []
    if StartValues.EnableConvertManager != True: return ExCode.StartFail
    if StartValues.EnableConvertManager == True: start_codes.append(_ConvertManager._start_converter(StartValues.ConvertModules, StartValues.ConvertClasses))
    if StartValues.EnableNetManager == True: start_codes.append(_NetManager._init_connection(StartValues.NetIsServer, StartValues.NetIp, StartValues.NetPort,
                                           StartValues.NetEncoding, StartValues.DefaultNetTimeout, StartValues.NetQueueSize))
    if StartValues.EnableUnixManager == True: start_codes.append(_UnixManager._init_connection(StartValues.UnixIsServer, StartValues.UnixPath,
                                           StartValues.UnixEncoding, StartValues.DefaultUnixTimeout, StartValues.UnixQueueSize))
    for exc in start_codes:
        if exc != ExCode.Success: return ExCode.StartFail
    return ExCode.Success

def stop():
    stop_codes = []
    if StartValues.EnableConvertManager == True: stop_codes.append(_ConvertManager._stop(prepare_mod=True))
    if StartValues.EnableNetManager == True: stop_codes.append(_NetManager._stop(prepare_mod=True))
    if StartValues.EnableUnixManager == True: stop_codes.append(_UnixManager._stop(prepare_mod=True))
    for exc in stop_codes:
        if exc != ExCode.Success: return ExCode.StopFail
    _ConvertManager._stop(prepare_mod=False)
    _NetManager._stop(prepare_mod=False)
    _UnixManager._stop(prepare_mod=False)
    return ExCode.Success

def accept_net_connection(client_timeout : int = StartValues.DefaultNetTimeout):
    return _NetManager._accept_connection(client_timeout)

def accept_unix_connection(client_timeout : int = StartValues.DefaultUnixTimeout):
    return _UnixManager._accept_connection(client_timeout)

def close_net_client_connection(client : _NetClient = StartValues.DefaultNetClient):
    return _NetManager._close_client_connection(client)

def close_unix_client_connection(client : _UnixClient = StartValues.DefaultUnixClient):
    return _UnixManager._close_client_connection(client)

def connect_to_net_srv():
    return _NetManager._connect_to_srv()

def connect_to_unix_srv():
    return _UnixManager._connect_to_srv()

def disconnect_from_net_srv():
    return _NetManager._disconnect_from_srv()

def disconnect_from_unix_srv():
    return _UnixManager._disconnect_from_srv()

def receive_data_over_net(bytes : int = StartValues.DefaultNetBytes, client : _NetClient = StartValues.DefaultNetClient):
    final_code = ExCode.Success
    data, excode = _NetManager._receive_data(client, bytes)
    if excode != ExCode.Success: final_code = excode
    netmes, loadcode = load_message_from_str(messtr=data)
    if loadcode != ExCode.Success and final_code == ExCode.Success: final_code = loadcode
    return netmes, final_code

def send_data_over_net(netmessage : _NetMessage, client : _NetClient = StartValues.DefaultNetClient):
    if type(netmessage) != _NetMessage : return ExCode.BadData
    if netmessage.create_code != ExCode.Success: return ExCode.BadData
    sendcode = _NetManager._send_data(client, netmessage.json_string)
    return sendcode

def receive_data_over_unix(bytes : int = StartValues.DefaultUnixBytes, client : _UnixClient = StartValues.DefaultUnixClient):
    final_code = ExCode.Success
    data, excode = _UnixManager._receive_data(client, bytes)
    if excode != ExCode.Success: final_code = excode
    netmes, loadcode = load_message_from_str(messtr=data)
    if loadcode != ExCode.Success and final_code == ExCode.Success: final_code = loadcode
    return netmes, final_code

def send_data_over_unix(netmessage : _NetMessage, client : _UnixClient = StartValues.DefaultUnixClient):
    if type(netmessage) != _NetMessage : return ExCode.BadData
    if netmessage.create_code != ExCode.Success: return ExCode.BadData
    sendcode = _UnixManager._send_data(client, netmessage.json_string)
    return sendcode
