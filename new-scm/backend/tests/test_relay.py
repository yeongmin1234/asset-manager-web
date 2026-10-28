"""Real Unix/TCP forwarding against a disposable local fake PostgreSQL peer."""
import asyncio
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from app.db import relay


@unittest.skipUnless(os.name == "posix", "Unix socket relay requires Linux")
class RelayTests(unittest.IsolatedAsyncioTestCase):
    async def test_ssl_probe_and_large_payload_round_trip(self):
        finished = asyncio.Event()

        async def upstream(reader, writer):
            try:
                probe = await reader.readexactly(8)
                self.assertEqual(probe, bytes.fromhex("0000000804d2162f"))
                writer.write(b"N")
                await writer.drain()
                while data := await reader.read(65536):
                    writer.write(data)
                    await writer.drain()
            finally:
                writer.close()
                await writer.wait_closed()
                finished.set()

        async with await asyncio.start_server(upstream, "127.0.0.1", 0) as tcp:
            target = tcp.sockets[0].getsockname()
            with tempfile.TemporaryDirectory(prefix="scm-relay-") as directory, \
                    patch.object(relay, "TARGET", target):
                path = str(Path(directory) / "db.sock")
                async with await asyncio.start_unix_server(relay.relay, path) as server:
                    reader, writer = await asyncio.open_unix_connection(path)
                    writer.write(bytes.fromhex("0000000804d2162f"))
                    await writer.drain()
                    self.assertEqual(await asyncio.wait_for(reader.readexactly(1), 3), b"N")
                    payload = bytes(range(256)) * 1024
                    writer.write(payload)
                    await writer.drain()
                    self.assertEqual(await asyncio.wait_for(reader.readexactly(len(payload)), 3), payload)
                    writer.close()
                    await writer.wait_closed()
                    await asyncio.wait_for(finished.wait(), 3)

    async def test_unavailable_upstream_closes_client(self):
        with tempfile.TemporaryDirectory(prefix="scm-relay-") as directory, socket.socket() as unavailable:
            unavailable.bind(("127.0.0.1", 0))  # Reserved but not listening.
            with patch.object(relay, "TARGET", unavailable.getsockname()):
                path = str(Path(directory) / "db.sock")
                async with await asyncio.start_unix_server(relay.relay, path):
                    reader, writer = await asyncio.open_unix_connection(path)
                    self.assertEqual(await asyncio.wait_for(reader.read(1), 3), b"")
                    writer.close()
                    await writer.wait_closed()

    async def test_serve_restricts_socket_permissions(self):
        with tempfile.TemporaryDirectory(prefix="scm-relay-") as directory:
            path = Path(directory) / "db.sock"
            old_umask = os.umask(0o077)
            try:
                with patch.object(relay, "SOCKET_PATH", str(path)):
                    task = asyncio.create_task(relay.serve())
                    try:
                        for _ in range(100):
                            if path.exists():
                                break
                            await asyncio.sleep(0.01)
                        self.assertEqual(path.stat().st_mode & 0o777, 0o700)
                    finally:
                        task.cancel()
                        await asyncio.gather(task, return_exceptions=True)
            finally:
                os.umask(old_umask)


if __name__ == "__main__":
    unittest.main()
