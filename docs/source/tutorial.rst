Tutorial
========

Nelambu is a small communication framework that provides RPC-style communication between
a server and one or more clients. Clients connect to the server and call functions,
then the server executes them and returns a result. Requests and responses are in the
form of byte buffers, so encoding and decoding them (e.g. using JSON or msgpack or
pickle) is up to the user.


Creating a server
-----------------

Before we can create a server, we need to create a handler object that will handle
requests. This is done by creating a class implementing the :py:class:`RequestHandler`
interface:


.. code-block:: python

    from typing import override
    from typing_extensions import Buffer
    from nelambu import RequestHandler


    class MyHandler(RequestHandler):
        @override
        def handle_request(self, request: Buffer) -> Buffer:
            req = self._decode_buffer(request)
            res = self._process_request(req)
            response = self._encode_buffer(res)

        def _decode_buffer(request: Buffer) -> list[Any]:
            # decode the buffer here

        def _process_request(request: list[Any]) -> list[Any]:
            # prepare the response here

        def _encode_buffer(response: list[Any]) -> Buffer:
            # encode the response here


The only function in :py:class:`RequestHandler` is
:py:meth:`~nelambu.RequestHandle.handle_request`. It takes a buffer, sent by the client,
and returns a buffer with the response to be returned. The implementation is up to you,
but generally you'll want to decode the request, process it (perhaps dispatching to
several different processing functions if your server needs to offer different functions
to call), and encode the response before returning it.

Note that as of Python 3.12, the ``Buffer`` type is available as
``collections.abc.Buffer``, so you should import it from there if you don't need
backwards compatibility.


.. code-block:: python

    from nelambu import TcpTransportServer

    # Create a server listening on port 10000
    handler = MyHandler()
    server = TcpTransportServer(handler, 10000)

    print(server.get_location())


Next, we can create an instance of the handler, and give it to a new
:py:class:`TcpTransportServer` object together with a port number. This will create a
new TCP server (the only protocol supported at the moment) listening on that port. Once
created, the network location of the server can be obtained via the
:py:meth:`~nelambu.TcpTransportServer.get_location` method.

The server will listen on all interfaces, and the location returned is in the form of a
string containing the addresses of all those interfaces plus the port number. This
string must be passed to the client somehow for it to use to connect to the server.


Creating a client
-----------------

With the location in hand, creating a client and connecting to the server is simple:

.. code-block:: python

    from nelambu import TcpTransportClient

    server_location = get_location()
    client = TcpTransportClient(server_location)

    req = encode_request()
    res = client.call(request)
    response = decode_response(res)


In case of network problems during the call, the client will automatically try to
reconnect and resubmit the request if needed, ensuring that the call is executed exactly
once. If the connection is lost after the request has been sent and reconnecting is not
possible within 60 seconds, then the client will give up and the response will be lost.

If a network error occurs and cannot be recovered, then
:py:meth:`~nelambu.TcpTransportClient.call` will raise a networking-related exception
describing the problem. This can be a ``ConnectionError`` or a ``TimeoutError``, or an
``OSError`` with ``errno`` set to ``EBADF`` or ``ENOTCONN``.


Shutting down
-------------

Both server and client keep an open connection around, which should be closed when done:

.. code-block:: python

    # blocks until the last request has been services
    server.close()

    # do not use call() after calling this
    client.close()


Timeouts
--------

RPC calls done with nelambu are blocking, meaning the client will wait indefinitely for
the server to return a response. If this is undesirable, a timeout handler may be
passed. This specifies a timeout, and will be notified if the server takes longer than
this period to respond. If such a notification has occurred, it will then also be
notified when the response arrives.

.. code-block:: python

    from typing import override
    from nelambu import TimeoutHandler


    class MyHandler(TimeoutHandler):
        @property
        def timeout(self) -> float:
            """Timeout (in seconds) after which on_timeout is called."""
            return 60.0

        @override
        def on_timeout(self) -> None:
            """Callback on peer timeout.

            Called when timeout seconds have passed without a response from the
            server.
            """
            print("Timed out!")

        @override
        def on_receive(self) -> None:
            """Callback when receiving a response from the server.

            Note: this method is only called when the request has previously timed out.
            """
            print("Response arrived after all")

    timeout_handler = MyHandler()
    req = encode_request()
    res = client.call(request, timeout_handler)


Aborting the call on timeout isn't currently possible. Raising an exception of a type
that isn't a network error on ``on_timeout()`` will abort the call to ``call()`` and
allow the client side to continue, but the request will still be pending, leading to a
resource leak on the server.


Profiling
---------

To profile calls (or do something else when the message is received), you can pass a
profile handler, in much the same way as the timeout handler above:

.. code-block:: python

    from nelambu import ProfileHandler


    class MyHandler(ProfileHandler):
        """Object handling profiling while receiving a message."""

        def on_start_wait(self) -> None:
            """Called after the request is sent."""

        def on_start_transfer(self) -> None:
            """Called when the response starts coming in."""

        def on_finish_transfer(self) -> None:
            """Called when the transfer is completed."""


    profile_handler = MyHandler()
    req = encode_request()
    res = client.call(request, None, profile_handler)


Logging
-------

The library will log various events to a logger named ``nelambu``, at log levels no
higher than ``logging.WARNING``. No handlers or log levels are set on this logger, so by
default the messages will be propagated to the root logger, which will in turn by
default only print the ones at ``logging.WARNING``.

To block all log output from nelambu, you can use

.. code-block:: python

    import logging


    logging.getLogger("nelambu").setLevel(logging.CRITICAL)


This will cause any log messages from nelambu at level lower than critical to get
dropped rather than propagated to the root logger, and that's all of them.

