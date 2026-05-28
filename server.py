import http.server
import socketserver
import json
import os
import sys
import hashlib
import uuid
import queue
import urllib.parse
import threading
from datetime import datetime

PORT = 8000
DB_FILE = 'database.json'
STATIC_DIR = 'public'

# Database Lock for thread safety
db_lock = threading.Lock()

# SSE clients list
sse_clients = []
sse_lock = threading.Lock()

# Setup default database
def init_db():
    with db_lock:
        if not os.path.exists(DB_FILE):
            # Create default admin user
            # admin / admin123
            salt = os.urandom(16)
            key = hashlib.pbkdf2_hmac('sha256', b'admin123', salt, 100000)
            default_admin = {
                "username": "admin",
                "password_hash": key.hex(),
                "salt": salt.hex(),
                "role": "admin",
                "fullname": "Administrador Carnicería"
            }
            
            default_data = {
                "users": [default_admin],
                "queue_state": {
                    "current": 0,
                    "last_number": 0,
                    "history": [] # items: {"number": int, "called_at": str, "called_by": str}
                },
                "sessions": {} # token: username
            }
            
            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, indent=4)
            print("[DB] Base de datos creada con usuario admin/admin123")

def read_db():
    with db_lock:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)

def write_db(data):
    with db_lock:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

# Security helpers
def hash_password(password, salt_hex=None):
    if salt_hex:
        salt = bytes.fromhex(salt_hex)
    else:
        salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return key.hex(), salt.hex()

def verify_password(password, salt_hex, password_hash):
    h, _ = hash_password(password, salt_hex)
    return h == password_hash

def broadcast_update(state):
    msg = f"data: {json.dumps(state)}\n\n"
    with sse_lock:
        for client in list(sse_clients):
            try:
                client.put_nowait(msg)
            except Exception:
                sse_clients.remove(client)

class ThreadingHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

class APIHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Override directory to look at public folder
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def log_message(self, format, *args):
        # Quiet logger for cleaner output, but can print errors if needed
        pass

    def check_auth(self):
        cookies = self.headers.get('Cookie', '')
        token = None
        if 'SessionToken=' in cookies:
            parts = cookies.split('SessionToken=')
            if len(parts) > 1:
                token = parts[1].split(';')[0]
        
        if not token:
            # Check Authorization header too
            auth_header = self.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
        
        if token:
            db = read_db()
            username = db.get("sessions", {}).get(token)
            if username:
                for u in db.get("users", []):
                    if u["username"] == username:
                        return u
        return None

    def send_json(self, data, status=200, cookies=None):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        
        if cookies:
            for k, v in cookies.items():
                self.send_header('Set-Cookie', f'{k}={v}; Path=/; HttpOnly; SameSite=Strict')
                
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def send_error_json(self, message, status=400):
        self.send_json({"error": message}, status)

    def read_post_json(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        try:
            return json.loads(post_data.decode('utf-8'))
        except Exception:
            return {}

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_GET(self):
        # Route API requests
        if self.path.startswith('/api/'):
            self.handle_api_get()
        else:
            # Fallback to serving static files
            # If path is root or folder, serve index.html
            parsed_path = urllib.parse.urlparse(self.path)
            path = parsed_path.path
            
            if path == '/' or path == '':
                self.path = '/index.html'
            elif not os.path.exists(os.path.join(STATIC_DIR, path.lstrip('/'))):
                # Simple SPA routing fallback to index.html if file doesn't exist
                self.path = '/index.html'
            
            super().do_GET()

    def do_POST(self):
        if self.path.startswith('/api/'):
            self.handle_api_post()
        else:
            self.send_error_json("Not Found", 404)

    def do_PUT(self):
        if self.path.startswith('/api/'):
            self.handle_api_put()
        else:
            self.send_error_json("Not Found", 404)

    def do_DELETE(self):
        if self.path.startswith('/api/'):
            self.handle_api_delete()
        else:
            self.send_error_json("Not Found", 404)

    # API Route Handlers
    def handle_api_get(self):
        db = read_db()
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        
        if path == '/api/turns/current':
            q = db["queue_state"]
            next_turn = q["current"] + 1 if q["current"] < q["last_number"] else None
            
            total_waiting = max(0, q["last_number"] - q["current"])
            self.send_json({
                "current": q["current"],
                "last_number": q["last_number"],
                "next": next_turn,
                "total_waiting": total_waiting,
                "history": q.get("history", [])[-5:] # last 5 calls
            })
            
        elif path == '/api/turns/live':
            # Server-Sent Events (SSE)
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            q = queue.Queue()
            with sse_lock:
                sse_clients.append(q)
            
            # Send current state initially
            qs = db["queue_state"]
            total_waiting = max(0, qs["last_number"] - qs["current"])
            initial_state = {
                "current": qs["current"],
                "last_number": qs["last_number"],
                "total_waiting": total_waiting,
                "history": qs.get("history", [])[-5:]
            }
            try:
                self.wfile.write(f"data: {json.dumps(initial_state)}\n\n".encode('utf-8'))
                self.wfile.flush()
            except Exception:
                with sse_lock:
                    if q in sse_clients:
                        sse_clients.remove(q)
                return

            # Loop keeping connection alive and sending updates
            while True:
                try:
                    msg = q.get(timeout=15.0)
                    self.wfile.write(msg.encode('utf-8'))
                    self.wfile.flush()
                except queue.Empty:
                    # Keep-alive Ping
                    try:
                        self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
                    except Exception:
                        break
                except Exception:
                    break
            
            with sse_lock:
                if q in sse_clients:
                    sse_clients.remove(q)

        elif path == '/api/auth/me':
            user = self.check_auth()
            if user:
                self.send_json({
                    "username": user["username"],
                    "fullname": user["fullname"],
                    "role": user["role"]
                })
            else:
                self.send_error_json("No autenticado", 401)

        elif path == '/api/users':
            user = self.check_auth()
            if not user or user["role"] != "admin":
                self.send_error_json("Acceso denegado", 403)
                return
            
            # Return list of users without password hashes
            users_list = []
            for u in db.get("users", []):
                users_list.append({
                    "username": u["username"],
                    "fullname": u["fullname"],
                    "role": u["role"]
                })
            self.send_json(users_list)
            
        else:
            self.send_error_json("Ruta API no encontrada", 404)

    def handle_api_post(self):
        db = read_db()
        path = urllib.parse.urlparse(self.path).path
        data = self.read_post_json()

        if path == '/api/auth/login':
            username = data.get('username')
            password = data.get('password')
            
            user = None
            for u in db.get("users", []):
                if u["username"] == username:
                    user = u
                    break
            
            if user and verify_password(password, user["salt"], user["password_hash"]):
                token = str(uuid.uuid4())
                db["sessions"][token] = username
                write_db(db)
                self.send_json({
                    "username": user["username"],
                    "fullname": user["fullname"],
                    "role": user["role"]
                }, cookies={"SessionToken": token})
            else:
                self.send_error_json("Usuario o contraseña incorrectos", 401)

        elif path == '/api/auth/logout':
            cookies = self.headers.get('Cookie', '')
            token = None
            if 'SessionToken=' in cookies:
                token = cookies.split('SessionToken=')[1].split(';')[0]
            
            if token and token in db.get("sessions", {}):
                del db["sessions"][token]
                write_db(db)
            
            self.send_json({"success": True}, cookies={"SessionToken": "deleted; Max-Age=0"})

        elif path == '/api/turns/take':
            # Client request for a turn
            q = db["queue_state"]
            q["last_number"] += 1
            new_turn = q["last_number"]
            ticket_id = str(uuid.uuid4())
            
            write_db(db)
            
            # Broadcast the update
            total_waiting = max(0, q["last_number"] - q["current"])
            broadcast_update({
                "current": q["current"],
                "last_number": q["last_number"],
                "total_waiting": total_waiting,
                "history": q.get("history", [])[-5:]
            })
            
            self.send_json({
                "number": new_turn,
                "id": ticket_id,
                "created_at": datetime.now().isoformat()
            })

        elif path == '/api/turns/next':
            # Butcher calls the next turn
            user = self.check_auth()
            if not user:
                self.send_error_json("No autenticado", 401)
                return
            
            q = db["queue_state"]
            if q["current"] < q["last_number"]:
                q["current"] += 1
                call_info = {
                    "number": q["current"],
                    "called_at": datetime.now().isoformat(),
                    "called_by": user["fullname"]
                }
                if "history" not in q:
                    q["history"] = []
                q["history"].append(call_info)
                write_db(db)
                
                total_waiting = max(0, q["last_number"] - q["current"])
                broadcast_update({
                    "current": q["current"],
                    "last_number": q["last_number"],
                    "total_waiting": total_waiting,
                    "history": q["history"][-5:],
                    "new_call": call_info # Signals the display screen to speak and animate
                })
                self.send_json({"success": True, "current": q["current"]})
            else:
                self.send_error_json("No hay más clientes en espera", 400)

        elif path == '/api/turns/recall':
            # Butcher repeats calling the current turn
            user = self.check_auth()
            if not user:
                self.send_error_json("No autenticado", 401)
                return
            
            q = db["queue_state"]
            if q["current"] > 0:
                call_info = {
                    "number": q["current"],
                    "called_at": datetime.now().isoformat(),
                    "called_by": user["fullname"],
                    "recall": True
                }
                total_waiting = max(0, q["last_number"] - q["current"])
                broadcast_update({
                    "current": q["current"],
                    "last_number": q["last_number"],
                    "total_waiting": total_waiting,
                    "history": q.get("history", [])[-5:],
                    "new_call": call_info
                })
                self.send_json({"success": True})
            else:
                self.send_error_json("No hay un turno activo para llamar", 400)

        elif path == '/api/turns/reset':
            # Admin resets queue
            user = self.check_auth()
            if not user:
                self.send_error_json("No autenticado", 401)
                return
            
            q = db["queue_state"]
            q["current"] = 0
            q["last_number"] = 0
            q["history"] = []
            write_db(db)
            
            broadcast_update({
                "current": 0,
                "last_number": 0,
                "total_waiting": 0,
                "history": [],
                "reset": True
            })
            self.send_json({"success": True})

        elif path == '/api/users':
            # Admin creates user
            user = self.check_auth()
            if not user or user["role"] != "admin":
                self.send_error_json("Acceso denegado", 403)
                return
            
            new_username = data.get("username", "").strip()
            new_password = data.get("password", "").strip()
            new_fullname = data.get("fullname", "").strip()
            new_role = data.get("role", "butcher")
            
            if not new_username or not new_password or not new_fullname:
                self.send_error_json("Faltan campos obligatorios", 400)
                return
            
            # Check if username exists
            for u in db.get("users", []):
                if u["username"] == new_username:
                    self.send_error_json("El usuario ya existe", 400)
                    return
            
            password_hash, salt = hash_password(new_password)
            db["users"].append({
                "username": new_username,
                "password_hash": password_hash,
                "salt": salt,
                "fullname": new_fullname,
                "role": new_role
            })
            write_db(db)
            self.send_json({"success": True})
            
        else:
            self.send_error_json("Ruta API no encontrada", 404)

    def handle_api_put(self):
        db = read_db()
        path = urllib.parse.urlparse(self.path).path
        data = self.read_post_json()

        if path.startswith('/api/users/'):
            user = self.check_auth()
            if not user or user["role"] != "admin":
                self.send_error_json("Acceso denegado", 403)
                return
            
            target_username = path.split('/api/users/')[1]
            found_user = None
            for u in db.get("users", []):
                if u["username"] == target_username:
                    found_user = u
                    break
            
            if not found_user:
                self.send_error_json("Usuario no encontrado", 404)
                return
            
            if "fullname" in data:
                found_user["fullname"] = data["fullname"]
            if "role" in data:
                found_user["role"] = data["role"]
            if "password" in data and data["password"].strip():
                password_hash, salt = hash_password(data["password"])
                found_user["password_hash"] = password_hash
                found_user["salt"] = salt
            
            write_db(db)
            self.send_json({"success": True})
        else:
            self.send_error_json("Ruta API no encontrada", 404)

    def handle_api_delete(self):
        db = read_db()
        path = urllib.parse.urlparse(self.path).path

        if path.startswith('/api/users/'):
            user = self.check_auth()
            if not user or user["role"] != "admin":
                self.send_error_json("Acceso denegado", 403)
                return
            
            target_username = path.split('/api/users/')[1]
            if target_username == "admin":
                self.send_error_json("No se puede eliminar el administrador por defecto", 400)
                return
                
            db["users"] = [u for u in db.get("users", []) if u["username"] != target_username]
            write_db(db)
            self.send_json({"success": True})
        else:
            self.send_error_json("Ruta API no encontrada", 404)

def run_server():
    init_db()
    
    # Ensure static public and assets dirs exist
    os.makedirs(os.path.join(STATIC_DIR, 'css'), exist_ok=True)
    os.makedirs(os.path.join(STATIC_DIR, 'js'), exist_ok=True)
    
    handler = APIHandler
    # Set default server address
    server_address = ('', PORT)
    
    try:
        httpd = ThreadingHTTPServer(server_address, handler)
        print(f"\n=======================================================")
        print(f" Servidor de Turnos 'Carnicería El Puntano' Activo!")
        print(f" URL Local: http://localhost:{PORT}")
        print(f" Credenciales de Admin: admin / admin123")
        print(f"=======================================================\n")
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nApagando servidor...")
        sys.exit(0)
    except Exception as e:
        print(f"Error al iniciar servidor: {e}")
        sys.exit(1)

if __name__ == '__main__':
    run_server()
