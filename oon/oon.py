import uuid as ud
import socket
import enum
import json

class ExCode(enum.Enum):
    Success     =   0
    StartFail   =   1
    StopFail    =   2
    BadData     =   3
    BadConn     =   4
    Timeout     =   5

DefaultIp               =   '127.0.0.1'
DefaultPort             =   9090
DefaultIsServer         =   True
DefaultEncoding         =   "utf-8"
DefaultTimeout          =   None
DefaultQueueSize        =   3
DefaultBytes            =   1024
DefaultNetClient        =   None

DefaultModules          =   []
DefaultNetobj           =   None
DefaultMessageString    =   None
DefaultIgnoreFields     =   []


class _ConvertManager(object):
    init    =   False
    modules =   None

    @staticmethod
    def _start_converter(modules : list):
        if _ConvertManager.init != False: return ExCode.StartFail
        _ConvertManager.modules = modules
        _ConvertManager.init = True
        return ExCode.Success

    @staticmethod
    def _generate_net_message(netobj, fields_to_ignore : list, uuid : str):
        if not _ConvertManager.init: return None, ExCode.StartFail
        new_network_message = _NetMessage(_ConvertManager.modules, netobj, fields_to_ignore, uuid)
        return new_network_message, new_network_message.create_code

    @staticmethod
    def _load_net_message_from_str(messtr : str, fields_to_ignore : list):
        if not _ConvertManager.init: return None, ExCode.StartFail
        old_network_message = _NetMessage(_ConvertManager.modules, messtr, fields_to_ignore)
        return old_network_message, old_network_message.create_code

    @staticmethod
    def _stop(prepare_mod : bool):
        if prepare_mod == True: return ExCode.Success
        _ConvertManager.modules = None
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
    def __init__(self, modules : list, body, fields_to_ignore : list, uuid : str = ud.uuid4().hex[:10]):
        netobj_list = []
        for mod in modules:
            for objcls in dir(mod):
                if isinstance(getattr(mod, objcls), type):
                    netobj_list.append(getattr(mod, objcls))
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
                final_netobj, final_create_code =  _NetMessage._netobj_from_dict(modules, mesdict["body"], fields_to_ignore)
        elif type(body) in netobj_list or body == None:
            final_netobj = body
            objdict, final_create_code = _NetMessage._netobj_to_dict(netobj_list, body, fields_to_ignore)
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
    def _netobj_to_dict(netobj_list, netobj, fields_to_ignore : list):
        if netobj == None: return {}, ExCode.BadData
        if type(netobj) not in netobj_list: return {}, ExCode.BadData
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
                if type(field_value) not in netobj_list: return objdict, ExCode.BadData
                objdict[field] = {"type":type(field_value).__name__, "value":field_value.value}
            elif type(field_value) in netobj_list:
                recobjdict, recexcode = _NetMessage._netobj_to_dict(netobj_list, field_value, fields_to_ignore)
                objdict[field] = recobjdict
                if recexcode != ExCode.Success: return objdict, recexcode
            else:
                objdict[field] = field_value
        return objdict, ExCode.Success

    @staticmethod
    def _netobj_from_dict(modules, objdict, fields_to_ignore : list):
        if objdict == {} or type(objdict) != dict or "type" not in objdict: return None, ExCode.BadData
        netobjmod = None
        for mod in modules:
            if hasattr(mod, objdict["type"]):
                netobjmod = mod
                break
        if netobjmod == None: return None, ExCode.BadData
        try:
            if type(getattr(netobjmod, objdict["type"])) == type(enum.Enum):
                return getattr(netobjmod, objdict["type"])(objdict["value"]),  ExCode.Success
            newnetobj = getattr(netobjmod, objdict["type"])()
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
                    subobj, excode = _NetMessage._netobj_from_dict(modules, objdict[field], fields_to_ignore)
                    setattr(newnetobj, field, subobj)
                    if excode != ExCode.Success: return newnetobj, excode
                except: return newnetobj, ExCode.BadData
            else:
                try: setattr(newnetobj, field, objdict[field])
                except: return newnetobj, ExCode.BadData
        return newnetobj, ExCode.Success





def generate_net_message(netobj = DefaultNetobj, fields_to_ignore : list = DefaultIgnoreFields, uuid : str = ud.uuid4().hex[:10]):
    return _ConvertManager._generate_net_message(netobj, fields_to_ignore, uuid)

def load_net_message_from_str(messtr : str = DefaultMessageString, fields_to_ignore : list = DefaultIgnoreFields):
    return _ConvertManager._load_net_message_from_str(messtr, fields_to_ignore)

def is_running():
    return _NetManager._status() and _ConvertManager._status()

def is_connected():
    return _NetManager._connect_status()

def turn_on(modules : list = DefaultModules, is_server : bool = DefaultIsServer, ip : str = DefaultIp, port : int = DefaultPort, encoding : str = DefaultEncoding, timeout : int = DefaultTimeout, queue_size : int = DefaultQueueSize):
    convcode = _ConvertManager._start_converter(modules)
    netcode = _NetManager._init_connection(is_server, ip, port, encoding, timeout, queue_size)
    if netcode != ExCode.Success or convcode != ExCode.Success:
        return ExCode.StartFail
    return ExCode.Success

def turn_off():
    convcode = _ConvertManager._stop(prepare_mod=True)
    netcode = _NetManager._stop(prepare_mod=True)
    if netcode != ExCode.Success or convcode != ExCode.Success: return ExCode.StopFail
    _ConvertManager._stop(prepare_mod=False)
    _NetManager._stop(prepare_mod=False)
    return ExCode.Success

def accept_net_connection(client_timeout : int = DefaultTimeout):
    return _NetManager._accept_connection(client_timeout)

def close_client_connection(client : _NetClient = DefaultNetClient):
    return _NetManager._close_client_connection(client)

def connect_to_srv():
    return _NetManager._connect_to_srv()

def disconnect_from_srv():
    return _NetManager._disconnect_from_srv()

def receive_data(bytes : int = DefaultBytes, client : _NetClient = DefaultNetClient):
    data, excode = _NetManager._receive_data(client, bytes)
    if excode != ExCode.Success: return data, excode
    netmes, loadcode = load_net_message_from_str(messtr=data)
    return netmes, loadcode

def send_data(netmessage : _NetMessage, client : _NetClient = DefaultNetClient):
    if type(netmessage) != _NetMessage : return ExCode.BadData
    if netmessage.create_code != ExCode.Success: return ExCode.BadData
    sendcode = _NetManager._send_data(client, netmessage.json_string)
    return sendcode
