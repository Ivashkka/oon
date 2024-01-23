<h1 align="center">OON
<h3 align="center">Objects Over Network protocol</h3>
<p>OON - module for python, which allows you to quickly and conveniently transfer objects of python classes over network</p>
<br>
<p><b>install:</b></p>
<p>install python oon module with pip:</p>
<p><code>pip3 install oon</code></p>
<br>
<p><b>usage:</b></p>
<p>OON is able to automaticly convert objects of your custom classes to dicts and strings and to form network message for transfering it</p>
<p>It can act like a server or a client depends on what you need</p>
<p>For example let's assume your python programs with some data related to cars and you have sepparate file cars.py with classes for different cars:</p>
<pre>

    ################# cars.py ###################
    import enum
    class CarMark(enum.Enum):
        Volvo = 0
        Toyota = 1
        Ford = 2

    class Car:
        mark : CarMark = None
        speed : int = None

    class TrucTrailer:
        car_inside : Car = None
        car_count : int = None

    class Truc(Car):
        trailer : TrucTrailer = None

    class VolvoCar(Car):
        __slots__ = ['wheels']
        mark = CarMark.Volvo
        def __init__(self, speed = 10, wheels = 4):
            self.speed = speed
            self.wheels = wheels
        def show_info(self):
            print(f"VolvoCar\n wheels:{self.wheels} speed:{self.speed}, mark:{self.mark}")

    class FordTruck(Truc):
        mark = CarMark.Ford
        def __init__(self, speed = 10, car : Car = None, count = 0):
            self.trailer = TrucTrailer()
            self.speed = speed
            self.trailer.car_inside = car
            self.trailer.car_count = count
        def show_info(self):
            print(f"FordTruck\n speed:{self.speed}, mark:{self.mark}, cars inside trailer:{self.trailer.car_count}")
            print(f"car inside trailer info:")
            self.trailer.car_inside.show_info()
</pre>
<p>So you also have main.py file where all other work done:</p>
<pre>

    ################# main.py ###################
    import cars    #import file with all classes defenitions

    my_car = cars.VolvoCar(speed=35, wheels=4)
    my_truck = cars.FordTruck(speed=20, car=my_car, count=1)
    print("\n")
    my_truck.show_info()   #show info about car
    print("\n")
</pre>
<p>Now you want to transfer <code>my_truck</code> object to other host. Let's assume this side will be server and other - client</p>
<p>To do this - just import oon and turn it on with server mode, wait for client connection and send your <code>my_truck</code> object:</p>
<p><b>Note: ALL FIELDS IN YOUR CLASSES MUST HAVE DEFAULT VALUES</b></p>
<p><b>also fields of type list, dict, tuple which contain several objects of other classes does not supported YET</b></p>
<pre>

    ################# new main.py - now server side ###################
    import oon     #import objects over network protocol
    import cars

    my_car = cars.VolvoCar(speed=35, wheels=4)
    my_truck = cars.FordTruck(speed=20, car=my_car, count=1)
    print("\n")
    my_truck.show_info()
    print("\n")

    exitcode = oon.turn_on(modules=[cars], is_server=True)   #turn on oon - returns ExCode
    if exitcode != oon.ExCode.Success:
        print(f"failed to start server! {exitcode}")
        exit(1)

    client, exitcode = oon.accept_net_connection()   #wait for client connection - returns object of _NetClient
    print(f"client with ip {client.addr}")
    if exitcode != oon.ExCode.Success:
        print(f"something wrong with connection or timeouted! {exitcode}")
        exit(1)

    netmessage, exitcode = oon.generate_net_message(my_truck)   #generate network message from your object - returns _NetMessage and ExCode
    if exitcode != oon.ExCode.Success:
        print(f"failed to generate network message! {exitcode}")

    exitcode = oon.send_data(netmessage, client)    #send generated message - returns ExCode
    if exitcode != oon.ExCode.Success:
        print(f"failed to transfer data! {exitcode}")

    oon.close_client_connection(client)    # close connection with client
    client = None
    exitcode = oon.turn_off()      #turn server off
    if exitcode == oon.ExCode.Success:
        print("server is off")
    else: print("failed to stop server")
</pre>
<p>now you can create <code>client.py</code> which will be client (it also needs cars.py file):</p>
<pre>

    ################# client.py ###################
    import oon
    import cars

    exitcode = oon.turn_on(modules=[cars], is_server=False)

    if exitcode != oon.ExCode.Success:
        print(f"failed to start client! {exitcode}")
        exit(1)

    exitcode = oon.connect_to_srv()
    if exitcode != oon.ExCode.Success:
        print(f"failed to connect to srv! {exitcode}")
        exit(1)

    netmessage, exitcode = oon.receive_data(bytes=1024)
    car = netmessage.netobj
    print("\n")
    car.show_info()
    print("\n")

</pre>
<p>now to test - start <code>python main.py</code> and <code>python client.py</code></p>
<p>on server:</p>
<pre>

    FordTruck
     speed:20, mark:CarMark.Ford, cars inside trailer:1
    car inside trailer info:
    VolvoCar
    wheels:4 speed:35, mark:CarMark.Volvo


    client with ip 127.0.0.1
    server is off
</pre>
<p>on client:</p>
<pre>

    FordTruck
     speed:20, mark:CarMark.Ford, cars inside trailer:1
    car inside trailer info:
    VolvoCar
    wheels:4 speed:35, mark:CarMark.Volvo
</pre>
<br>
<br>
<p><b>docs:</b></p>
<p>info about all supported data types, all available functions, returns and objects:</p>
<p>all functions:</p>
<table border="2">
  <thead>
    <tr>
      <th>Function</th>
      <th>Parameters</th>
      <th>Purpose</th>
      <th>Condition to Use</th>
      <th>Return</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><b>turn_on()</b></td>
      <td><b>modules : list</b> - list of modules with your custom classes,<br><b>classes : list</b> - list of your custom unit classes which aren't located in your modules,<br><b>is_server : bool</b> - start as server or as client,<br><b>ip : str</b> - ip,<br><b>port : int</b> - port,<br><b>encoding : str</b> - what encoding to use,<br><b>timeout : int</b> - timeout of future operations,<br><b>queue_size : int</b> - size of connections in queue</td>
      <td>start oon</td>
      <td>if not started</td>
      <td><b>ExCode.Success</b> or <b>ExCode.StartFail</b></td>
    </tr>
    <tr>
      <td><b>turn_off()</b></td>
      <td>no</td>
      <td>turn off oon</td>
      <td>if started and if no clients active if in server mode</td>
      <td><b>ExCode.Success</b> or <b>ExCode.StopFail</b><br>If StopFail on server mode - maybe some clients are still active, close them before stopping</td>
    </tr>
    <tr>
      <td><b>accept_net_connection()</b></td>
      <td><b>client_timeout : int</b> - timeout of future operations with client connection</td>
      <td>wait for client connection until timeout</td>
      <td>if started in server mode</td>
      <td><b>(_NetClient, ExCode.Success)</b> - if all ok<br><b>(None, ExCode.BadConn)</b> - if something wrong with listening socket<br><b>(None, ExCode.Timeout)</b> - if timeouted<br><b>(None, ExCode.StartFail)</b> - if you forgot to start oon</td>
    </tr>
    <tr>
      <td><b>close_client_connection()</b></td>
      <td><b>client : _NetClient</b> - client</td>
      <td>close connection with client</td>
      <td>if started in server mode</td>
      <td><b>(_NetClient, ExCode.Success)</b> - if all ok<br><b>(None, ExCode.BadConn)</b> - if something wrong with client<br><b>(None, ExCode.StartFail)</b> - if you forgot to start oon</td>
    </tr>
    <tr>
      <td><b>connect_to_srv()</b></td>
      <td>no</td>
      <td>connect to server</td>
      <td>if started in client mode and not connected</td>
      <td><b>ExCode.Success</b> - if all ok<br><b>ExCode.BadConn</b> - if something wrong with connection, or already connected<br><b>ExCode.Timeout</b> - if timeouted<br><b>ExCode.StartFail</b> - if you forgot to start oon</td>
    </tr>
    <tr>
      <td><b>disconnect_from_srv()</b></td>
      <td>no</td>
      <td>disconnect from server</td>
      <td>if started in client mode and connected</td>
      <td><b>ExCode.Success</b> - if all ok<br><b>ExCode.BadConn</b> - if something wrong with connection, or already disconnected<br><b>ExCode.Timeout</b> - if timeouted<br><b>ExCode.StartFail</b> - if you forgot to start oon</td>
    </tr>
    <tr>
      <td><b>generate_net_message()</b></td>
      <td>netobj : Any - object you want to transfer,<br>fields_to_ignore : list - what fileds of object you don't want to transfer,<br>uuid : str - generated if nothing specified</td>
      <td>generate network message</td>
      <td>if started</td>
      <td><b>(_NetMessage, ExCode.Success)</b> - if all ok<br><b>(_NetMessage, ExCode.BadData)</b> - if your objects does not meet the requirements<br><b>(None, ExCode.StartFail)</b> - if you forgot to start oon</td>
    </tr>
    <tr>
      <td><b>load_net_message_from_str()</b></td>
      <td>messtr : str - json string,<br>fields_to_ignore : list - field not to load from string</td>
      <td>load network message from it's json string variant. Uses automatically inside <b>receive_data()</b> method</td>
      <td>if started</td>
      <td><b>(_NetMessage, ExCode.Success)</b> - if all ok<br><b>(_NetMessage, ExCode.BadData)</b> - if something wrong with json string or with your classes in your module<br><b>(None, ExCode.StartFail)</b> - if you forgot to start oon</td>
    </tr>
    <tr>
      <td><b>receive_data()</b></td>
      <td>bytes : int - size of message to expect,<br>client : _NetClient - client. Only if started in server mode!</td>
      <td>receive data from client or server</td>
      <td>if started. If in client mode, needs to be connected to server</td>
      <td><b>(_NetMessage, ExCode.Success)</b> - if all ok<br><b>(_NetMessage, ExCode.BadData)</b> - if failed to <b>load_net_message_from_str()</b><br><b>(None, ExCode.BadConn)</b> - if something wrong with connection<br><b>(None, ExCode.Timeout)</b> - if timeouted<br><b>(None, ExCode.StartFail)</b> - if you forgot to start oon</td>
    </tr>
    <tr>
      <td><b>send_data()</b></td>
      <td>netmessage : _NetMessage - generated network message,<br>client : _NetClient - client. Only if started in server mode!</td>
      <td>send data to client or server</td>
      <td>if started. If in client mode, needs to be connected to server</td>
      <td><b>ExCode.Success</b> - if all ok<br><b>ExCode.BadData</b> - if you give strange data<br><b>ExCode.BadConn</b> - if something wrong with client<br><b>ExCode.Timeout</b> - if timeouted<br><b>ExCode.StartFail</b> - if you forgot to start oon</td>
    </tr>
    <tr>
      <td><b>is_running()</b></td>
      <td>no</td>
      <td>get info about oon status</td>
      <td>no</td>
      <td><b>True</b> - running<br><b>False</b> - not running</td>
    </tr>
    <tr>
      <td><b>is_connected()</b></td>
      <td>no</td>
      <td>get info about connect status (Does not tell info about other side connection state!)</td>
      <td>if started in client mode</td>
      <td><b>True</b> - connected<br><b>False</b> - not connected</td>
    </tr>
  </tbody>
</table>
<br>
<p>all objects:</p>
<br>
<p><b>_NetMessage (message for transfering between hosts):</b></p>
<table border="2">
  <thead>
    <tr>
      <th>Field</th>
      <th>Purpose</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><b>create_code : ExCode</b></td>
      <td>signals if object created as expected. This field returns as exitcode of related functions when generating or loading message</td>
    </tr>
    <tr>
      <td><b>json_string : str</b></td>
      <td>message in json string form, this is data that is actually being transferred</td>
    </tr>
    <tr>
      <td><b>netobj : Any</b></td>
      <td>actual object from your custom module</td>
    </tr>
    <tr>
      <td><b>uuid : str</b></td>
      <td>uuid of message</td>
    </tr>
  </tbody>
</table>
<br>
<p><b>_NetClient (container for all data related to client connection):</b></p>
<table border="2">
  <thead>
    <tr>
      <th>Field</th>
      <th>Purpose</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><b>alive : Bool</b></td>
      <td>if connection wasn't closed manually.This field does not reflect the connection status at the other end</td>
    </tr>
    <tr>
      <td><b>socket : socket.socket</b></td>
      <td>clisent connection socket</td>
    </tr>
    <tr>
      <td><b>addr : str</b></td>
      <td>ip</td>
    </tr>
    <tr>
      <td><b>port : int</b></td>
      <td>port</td>
    </tr>
    <tr>
      <td><b>uuid : str</b></td>
      <td>uuid</td>
    </tr>
  </tbody>
</table>
<br>
<p>usefull info:<p>
<p><b>ExCode.BadConn</b> in most cases means that connection was closed by other side, or you are transmitting wrong data to the function</p>
<p>Every function argument has default value. You can change it.</p>
<br>
<p>Note: this module was originally developed as part of a NAM project - https://github.com/Ivashkka/nam <p>
