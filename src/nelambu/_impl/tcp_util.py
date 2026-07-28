from errno import EBADF
from errno import ENOTCONN
from socket import SocketType
from typing_extensions import Buffer
from nelambu._impl import mark
from nelambu._impl.transport_client import ProfileHandler


class SocketClosedError(ConnectionError):
    """Raised when trying to read from a socket that was closed."""


_CONNECTION_ERRORS = (BrokenPipeError, ConnectionError, SocketClosedError, TimeoutError)


_CONNECTION_ERRNOS = (EBADF, ENOTCONN)


def is_disconnect(exception: Exception) -> bool:
    """Checks whether this is a disconnect or another problem."""
    if isinstance(exception, _CONNECTION_ERRORS):
        return True
    return isinstance(exception, OSError) and exception.errno in _CONNECTION_ERRNOS


def recv_all(socket: SocketType, length: int) -> Buffer:
    """Receive length bytes from a socket.

    Args:
        socket: Socket to receive on.
        length: Number of bytes to receive.

    Raises:
        SocketClosed: If the socket was closed by the peer.
        RuntimeError: If a read error occurred.
    """
    databuf = bytearray(length)
    received_count = 0
    while received_count < length:
        mark.before_tcp_receive(socket)
        bytes_left = length - received_count
        received_now = socket.recv_into(
            memoryview(databuf)[received_count:], bytes_left
        )

        if received_now == 0:
            raise SocketClosedError("Socket closed while receiving")

        if received_now == -1:
            raise RuntimeError("Error receiving")

        received_count += received_now

    return databuf


def send_int64(socket: SocketType, data: int) -> None:
    """Sends an int as a 64-bit signed little endian number.

    Args:
        socket: The socket to send on.
        data: The number to send.

    Raises:
        RuntimeError: If there was an error sending the data.
    """
    buf = data.to_bytes(8, byteorder="little")
    mark.before_tcp_send(socket)
    socket.sendall(buf)


def recv_int64(socket: SocketType) -> int:
    """Receives an int as a 64-bit signed little endian number.

    Args:
        socket: The socket to receive on.

    Raises:
        SocketClosed: If the socket was closed by the peer.
        RuntimeError: If a read error occurred.
    """
    mark.before_tcp_receive(socket)
    buf = recv_all(socket, 8)
    return int.from_bytes(buf, "little")


def send_frame(socket: SocketType, data: Buffer) -> None:
    """Sends a frame as length + data.

    Args:
        socket: The socket to send on
        data: The data to send

    Raises:
        RuntimeError: If there was an error sending the data.
    """
    send_int64(socket, len(memoryview(data)))
    socket.sendall(data)


def recv_frame(
    socket: SocketType, profile_handler: ProfileHandler | None = None
) -> Buffer:
    """Receives a frame as length + data.

    Args:
        socket: The socket to receive on
        profile_handler: A profile handler to notify when the transfer starts

    Returns:
        The received data.

    Raises:
        RuntimeError: If there was an error receiving the data.
    """
    length = recv_int64(socket)

    if profile_handler:
        profile_handler.on_start_transfer()

    return recv_all(socket, length)
