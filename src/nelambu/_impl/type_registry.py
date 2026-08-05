from nelambu._impl.tcp_transport_client import TcpTransportClient
from nelambu._impl.tcp_transport_server import TcpTransportServer
from nelambu._impl.transport_client import TransportClient

# These must be in order of preference, i.e. most efficient first
transport_client_types = [TcpTransportClient]


transport_server_types = [TcpTransportServer]


def client_for(location: str) -> TransportClient:
    """Return a client for connecting to the given location.

    Args:
        location: The location to connect to. Must be obtained from
            :meth:`TransportServer.get_location`.

    Returns:
        A :class:`TransportClient` connected to the given location.

    Raises:
        RuntimeError: If no client type could be found for the given location.
    """
    for client_type in transport_client_types:
        if client_type.can_connect_to(location):
            return client_type(location)
    raise RuntimeError(f"Unexpected location {location}")
