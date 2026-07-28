import math
import time
from collections.abc import Generator
from random import choice
from random import random
from random import uniform
from socket import SHUT_RD
from socket import SHUT_RDWR
from socket import SHUT_WR
from socket import SocketType
from typing import override
from unittest.mock import patch
import pytest
from typing_extensions import Buffer
from nelambu import RequestHandler
from nelambu import TcpTransportClient
from nelambu import TcpTransportServer

_FAULT_PROB_MAX = 0.1


_start_time = 0
_repeat_period = 0.0

_loops = 500
_data_scale = 500


def _inject_fault(socket: SocketType) -> None:
    """Randomly closes the socket to simulate a dropped connection."""
    t = math.fmod((time.monotonic_ns() - _start_time) / 1e9, _repeat_period)
    fault_prob = 0.0
    if 0.0 < t < 1.0:
        fault_prob = t * _FAULT_PROB_MAX
    elif 1.0 < t < 2.0:  # noqa: PLR2004
        fault_prob = _FAULT_PROB_MAX
    elif 2.0 < t < 3.0:  # noqa: PLR2004
        fault_prob = (3.0 - t) * _FAULT_PROB_MAX

    if random() < fault_prob:
        mode = choice((SHUT_RD, SHUT_WR, SHUT_RDWR))
        socket.shutdown(mode)


@pytest.fixture
def tcp_fault_injection() -> Generator[None, None, None]:
    with (
        patch("nelambu._impl.mark.before_tcp_receive", _inject_fault),
        patch("nelambu._impl.mark.before_tcp_send", _inject_fault),
    ):
        yield


class MirrorHandler(RequestHandler):
    @override
    def handle_request(self, request: Buffer) -> Buffer:
        return request


# def test_python_tcp_reconnect() -> None:
def test_python_tcp_reconnect(tcp_fault_injection: None) -> None:
    global _start_time, _repeat_period  # noqa: PLW0603
    _start_time = time.monotonic_ns()
    _repeat_period = uniform(3.0, 5.0)

    handler = MirrorHandler()
    server = TcpTransportServer(handler, 9001)
    client = TcpTransportClient(server.get_location())

    for i in range(_loops):
        request = b"i" * (i * _data_scale)
        response = client.call(request)
        assert response == request

    client.close()
    server.close()
