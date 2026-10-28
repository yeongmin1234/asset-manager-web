"""Private Unix socket -> existing NAS loopback PostgreSQL publication.

No Docker socket, database credentials, TCP listener, or application imports.
Run one relay under UID 10001 with its own host network namespace access.
"""
import asyncio
import os
from pathlib import Path
import socket
import stat
import sys

SOCKET_PATH = "/srv/new-scm/db-socket/.s.PGSQL.15432"
TARGET = ("127.0.0.1", 15432)


async def forward(reader, writer):
    while data := await reader.read(65536):
        writer.write(data)
        await writer.drain()
    if writer.can_write_eof():
        writer.write_eof()


async def relay(client_reader, client_writer):
    upstream_writer = None
    tasks = []
    try:
        upstream_reader, upstream_writer = await asyncio.wait_for(
            asyncio.open_connection(*TARGET), timeout=3,
        )
        tasks = [asyncio.create_task(forward(client_reader, upstream_writer)),
                 asyncio.create_task(forward(upstream_reader, client_writer))]
        # A hung/disconnected client must not leave an upstream connection behind.
        await asyncio.wait_for(asyncio.gather(*tasks), timeout=3600)
    except (OSError, TimeoutError):
        pass  # Never log payloads or connection exception details.
    finally:
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        for writer in (client_writer, upstream_writer):
            if writer is not None:
                writer.close()
                try:
                    await writer.wait_closed()
                except OSError:
                    pass


async def serve():
    os.umask(0o077)
    path = Path(SOCKET_PATH)
    if path.exists():
        if not stat.S_ISSOCK(path.stat().st_mode):
            raise OSError("relay_socket_path_rejected")
        path.unlink()
    async with await asyncio.start_unix_server(relay, path=SOCKET_PATH) as server:
        await server.serve_forever()


def check():
    with socket.socket(socket.AF_UNIX) as connection:
        connection.settimeout(3)
        connection.connect(SOCKET_PATH)
        # PostgreSQL SSLRequest; accept SSL available/unavailable, no credentials.
        connection.sendall(bytes.fromhex("0000000804d2162f"))
        if connection.recv(1) not in (b"S", b"N"):
            raise OSError("relay_upstream_unavailable")


if __name__ == "__main__":
    try:
        if sys.argv[1:] == ["--check"]:
            check()
        elif not sys.argv[1:]:
            asyncio.run(serve())
        else:
            raise ValueError()
    except (OSError, ValueError):
        sys.exit("relay_unavailable")
