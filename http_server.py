import http.server
import socketserver
import os

PORT = 8000
DIRECTORY = "templates"

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.path = "index.html"
        
        file_path = os.path.join(DIRECTORY, self.path.lstrip("/"))
        
        if os.path.exists(file_path) and os.path.isfile(file_path):
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            with open(file_path, "rb") as file:
                self.wfile.write(file.read())
        else:
            self.send_error(404, "File Not Found")

handler = CustomHandler

with socketserver.TCPServer(("", PORT), handler) as httpd:
    print(f"Serving HTTP on port {PORT}...")
    httpd.serve_forever()
