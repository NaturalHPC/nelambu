import os
import time
from collections.abc import Generator
from unittest.mock import MagicMock
import pytest
from typing_extensions import override
from nelambu._impl.tcp_transport_client import TcpTransportClient
from nelambu._impl.tcp_transport_server import TcpTransportServer
from nelambu._impl.transport_client import ProfileHandler
from nelambu._impl.transport_client import TimeoutHandler
from nelambu._impl.type_registry import client_for

_SERVER_DELAY = 0.2


@pytest.fixture
def server() -> Generator[str, None, None]:
    def handle_request(request: bytes) -> bytes:
        assert request == b"request"
        return b"response"

    request_handler = MagicMock()
    request_handler.handle_request = handle_request
    server = TcpTransportServer(request_handler)
    yield server.get_location()
    server.close(False)


def test_tcp_transport(server: str) -> None:
    request = b"request"
    expected_response = b"response"

    # create client
    assert TcpTransportClient.can_connect_to(server)
    client = TcpTransportClient(server)

    actual_response = client.call(request)
    assert actual_response == expected_response

    client.close()


def test_client_for(server: str) -> None:
    request = b"request"
    expected_response = b"response"

    # create client
    client = client_for(server)

    actual_response = client.call(request)
    assert actual_response == expected_response

    client.close()


@pytest.fixture
def slow_server() -> Generator[str, None, None]:

    def handle_request(request: bytes) -> bytes:
        assert request == b"request"
        time.sleep(_SERVER_DELAY)
        return b"response"

    request_handler = MagicMock()
    request_handler.handle_request = handle_request
    server = TcpTransportServer(request_handler)
    yield server.get_location()
    server.close(False)


def test_client_timeout(slow_server: str) -> None:
    timeout_detected = False
    received = False

    class Handler(TimeoutHandler):
        def __init__(self) -> None:
            self.timeout_ = 0.1

        @property
        def timeout(self) -> float:
            return self.timeout_

        @override
        def on_timeout(self) -> None:
            nonlocal timeout_detected
            timeout_detected = True

        @override
        def on_receive(self) -> None:
            nonlocal received
            received = True

    timeout_handler = Handler()
    client = TcpTransportClient(slow_server)
    client.call(b"request", timeout_handler)

    assert timeout_detected
    assert received

    timeout_detected = False
    received = False
    timeout_handler.timeout_ = 1.0

    client.call(b"request", timeout_handler)

    assert not timeout_detected
    assert not received

    client.close()


def test_profiling_handler(slow_server: str) -> None:
    expected_transfer_time = 0.1

    class Handler(ProfileHandler):
        def __init__(self) -> None:
            self.start_wait = None
            self.start_transfer = None
            self.finish_transfer = None

        def on_start_wait(self) -> None:
            self.start_wait = time.monotonic()

        def on_start_transfer(self) -> None:
            self.start_transfer = time.monotonic()

        def on_finish_transfer(self) -> None:
            self.finish_transfer = time.monotonic()

    profiling_handler = Handler()
    client = TcpTransportClient(slow_server)
    client.call(b"request", None, profiling_handler)

    assert profiling_handler.start_wait is not None
    assert profiling_handler.start_transfer is not None
    assert profiling_handler.finish_transfer is not None

    wait_time = profiling_handler.start_transfer - profiling_handler.start_wait
    transfer_time = profiling_handler.finish_transfer - profiling_handler.start_transfer

    # unreliable on GitHub Actions
    if "CI" not in os.environ:
        assert _SERVER_DELAY <= wait_time < (_SERVER_DELAY + 0.1)
        assert transfer_time < expected_transfer_time

    client.close()
