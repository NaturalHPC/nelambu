from collections.abc import Generator
from unittest.mock import MagicMock
import pytest
from nelambu._impl.tcp_transport_server import TcpTransportServer


@pytest.fixture
def tcp_transport_server() -> Generator[TcpTransportServer, None, None]:
    server = TcpTransportServer(MagicMock())
    yield server
    server.close()
