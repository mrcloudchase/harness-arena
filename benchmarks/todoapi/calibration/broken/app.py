import http.server
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self)
        self.wfile.write(b'[]')
http.server.HTTPServer(('', 8000), H).serve_forever()
