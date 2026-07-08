import argparse
import functools
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


class AssetManagerStaticHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        request_path = self.path.split("?", 1)[0]
        if request_path in ("", "/", "/index.html"):
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
        elif request_path.startswith("/assets/"):
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        else:
            self.send_header("Cache-Control", "no-cache")
        SimpleHTTPRequestHandler.end_headers(self)

    def translate_path(self, path):
        resolved_path = SimpleHTTPRequestHandler.translate_path(self, path)
        if os.path.exists(resolved_path):
            return resolved_path
        request_path = self.path.split("?", 1)[0]
        if request_path.startswith("/assets/") or os.path.splitext(request_path)[1]:
            return resolved_path
        return os.path.join(self.directory, "index.html")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=3010)
    parser.add_argument("--directory", required=True)
    args = parser.parse_args()

    handler = functools.partial(
        AssetManagerStaticHandler,
        directory=os.path.abspath(args.directory),
    )
    server = ThreadingHTTPServer((args.host, args.port), handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
