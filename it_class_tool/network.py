# -*- coding: utf-8 -*-
"""网络层：纯 P2P 聊天节点，无独立服务端。

- UDP 广播：局域网发现（hello/bye）与群聊（group_msg）
- TCP 点对点：私聊（private_msg）与送达回执（ack）
节点通过事件队列向外（界面层）投递事件，事件是 (type, payload) 二元组：
    ("peers", snapshot) / ("private", msg) / ("group", msg) / ("ack", msg)
    ("self_nick", nick) / ("notice", text)
"""
import json
import socket
import threading
import time
import uuid

from .config import (
    APP_MAGIC,
    DISCOVERY_PORT,
    HEARTBEAT_INTERVAL,
    PEER_TIMEOUT,
)


class ChatNode:
    def __init__(self, nick, event_queue):
        self.uid = uuid.uuid4().hex[:10]
        self.base_nick = nick
        self.nick = nick
        self.nick_fixed = False
        self.q = event_queue
        self.running = True

        self.peers = {}
        self.peers_lock = threading.Lock()

        self.out_conns = {}
        self.in_conns = {}
        self.conns_lock = threading.Lock()
        self.tcp_port = 0
        self.udp_sock = None
        self.tcp_sock = None
        self.broadcast_targets = []
        self.local_ip = "127.0.0.1"
        self._last_sig = None

        self._seen_group = {}
        self._seen_group_lock = threading.Lock()
        self._seen_group_ttl = 120.0
        self._seen_group_max = 2000

        self._compute_broadcast_targets()

    def start(self):
        if not self._start_tcp():
            self.q.put(("notice", "TCP 监听启动失败，将无法接收私聊"))
        self._start_udp()
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()
        threading.Thread(target=self._cleanup_loop, daemon=True).start()

    def stop(self):
        if not self.running:
            return
        self.running = False
        try:
            self._broadcast_udp({"magic": APP_MAGIC, "type": "bye",
                                 "uid": self.uid, "timestamp": time.time()})
        except Exception:
            pass
        for s in (self.udp_sock, self.tcp_sock):
            try:
                if s:
                    s.close()
            except OSError:
                pass
        with self.conns_lock:
            for s in list(self.out_conns.values()) + list(self.in_conns.values()):
                try:
                    s.close()
                except OSError:
                    pass
            self.out_conns.clear()
            self.in_conns.clear()

    def _compute_broadcast_targets(self):
        ips = set()
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            s.connect(("8.8.8.8", 80))
            ips.add(s.getsockname()[0])
            s.close()
        except OSError:
            pass
        try:
            for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
                ips.add(ip)
        except OSError:
            pass
        ips = {ip for ip in ips if not ip.startswith("127.")}
        if ips:
            self.local_ip = sorted(ips)[0]
        targets = {"255.255.255.255"}
        for ip in ips:
            p = ip.split(".")
            if len(p) == 4:
                targets.add(".".join(p[:3]) + ".255")
                targets.add(".".join(p[:2]) + ".255.255")
        self.broadcast_targets = sorted(targets)

    def _start_tcp(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("", 0))
            s.listen(64)
            self.tcp_sock = s
            self.tcp_port = s.getsockname()[1]
            threading.Thread(target=self._accept_loop, args=(s,), daemon=True).start()
            return True
        except OSError:
            return False

    def _accept_loop(self, srv):
        while self.running:
            try:
                conn, addr = srv.accept()
            except OSError:
                break
            threading.Thread(target=self._conn_reader,
                             args=(conn, addr), daemon=True).start()

    def _conn_reader(self, conn, addr):
        buf = b""
        try:
            while self.running:
                try:
                    chunk = conn.recv(8192)
                except OSError:
                    break
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        msg = json.loads(line.decode("utf-8"))
                    except Exception:
                        continue
                    try:
                        self._handle_tcp_message(msg, conn, addr)
                    except Exception:
                        pass
        finally:
            self._drop_conn(conn)

    def _drop_conn(self, conn):
        with self.conns_lock:
            for d in (self.out_conns, self.in_conns):
                for k in [k for k, v in d.items() if v is conn]:
                    del d[k]
        try:
            conn.close()
        except OSError:
            pass

    def _send_line(self, sock, obj):
        data = (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")
        sock.sendall(data)

    def _handle_tcp_message(self, msg, conn, addr):
        mtype = msg.get("type")
        sender = msg.get("from")
        if sender and sender != self.uid:
            with self.conns_lock:
                self.in_conns[sender] = conn
            need_pub = False
            with self.peers_lock:
                now = time.time()
                if sender in self.peers:
                    p = self.peers[sender]
                    was_online = p.get("online", False)
                    p["last_seen"] = now
                    p["online"] = True
                    if isinstance(msg.get("from_port"), int):
                        p["tcp_port"] = msg["from_port"]
                        p["ip"] = msg.get("from_ip") or addr[0]
                        if msg.get("from_nick"):
                            p["nick"] = str(msg["from_nick"])[:32]
                    need_pub = not was_online
                elif isinstance(msg.get("from_port"), int):
                    self.peers[sender] = {
                        "nick": str(msg.get("from_nick") or "未知")[:32],
                        "ip": msg.get("from_ip") or addr[0],
                        "tcp_port": msg["from_port"],
                        "last_seen": now,
                        "online": True,
                    }
                    need_pub = True
            if need_pub:
                self._publish_peers()

        if mtype == "private_msg":
            self.q.put(("private", msg))
            ack = {"type": "ack", "from": self.uid, "to": sender,
                   "messageId": msg.get("messageId"), "timestamp": time.time()}
            try:
                self._send_line(conn, ack)
            except OSError:
                pass
        elif mtype == "ack":
            self.q.put(("ack", msg))

    def _connect_to(self, uid, ip, port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3.0)
        try:
            s.connect((ip, port))
        except OSError:
            s.close()
            raise
        s.settimeout(None)
        with self.conns_lock:
            old = self.out_conns.get(uid)
            self.out_conns[uid] = s
        if old and old is not s:
            try:
                old.close()
            except OSError:
                pass
        threading.Thread(target=self._conn_reader, args=(s, (ip, port)), daemon=True).start()
        return s

    def _get_send_socket(self, uid, peer=None):
        with self.conns_lock:
            s = self.out_conns.get(uid)
            if s:
                return s
            s = self.in_conns.get(uid)
            if s:
                return s
        if peer is None:
            with self.peers_lock:
                peer = self.peers.get(uid)
        if not peer:
            return None
        try:
            return self._connect_to(uid, peer["ip"], peer["tcp_port"])
        except OSError:
            return None

    def _start_udp(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            s.bind(("", DISCOVERY_PORT))
        except OSError:
            try:
                s.bind(("", 0))
            except OSError:
                s.close()
                self.q.put(("notice", "UDP 端口绑定失败，无法进行局域网发现"))
                return
        s.settimeout(1.0)
        self.udp_sock = s
        threading.Thread(target=self._udp_loop, daemon=True).start()

    def _udp_loop(self):
        while self.running:
            sock = self.udp_sock
            if sock is None:
                break
            try:
                data, addr = sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                msg = json.loads(data.decode("utf-8"))
            except Exception:
                continue
            if msg.get("magic") != APP_MAGIC:
                continue
            self._handle_udp(msg, addr)

    def _handle_udp(self, msg, addr):
        mtype = msg.get("type")
        if mtype == "hello":
            self._handle_hello(msg, addr)
        elif mtype == "bye":
            uid = msg.get("uid")
            if uid and uid != self.uid:
                changed = False
                with self.peers_lock:
                    if uid in self.peers and self.peers[uid]["online"]:
                        self.peers[uid]["online"] = False
                        changed = True
                if changed:
                    self._publish_peers()
        elif mtype == "group_msg":
            if msg.get("from") == self.uid:
                return
            mid = msg.get("messageId")
            if mid:
                now = time.time()
                with self._seen_group_lock:
                    if len(self._seen_group) > self._seen_group_max // 2:
                        expired = [k for k, v in self._seen_group.items()
                                   if now - v > self._seen_group_ttl]
                        for k in expired:
                            del self._seen_group[k]
                    if mid in self._seen_group:
                        return
                    self._seen_group[mid] = now
                    if len(self._seen_group) > self._seen_group_max:
                        oldest = min(self._seen_group.items(), key=lambda x: x[1])[0]
                        del self._seen_group[oldest]
            self.q.put(("group", msg))

    def _handle_hello(self, msg, addr):
        uid = msg.get("uid")
        port = msg.get("tcp_port")
        if not uid or uid == self.uid or not isinstance(port, int) or port <= 0:
            return
        nick = str(msg.get("nick") or "未知")[:32]

        with self.peers_lock:
            now = time.time()
            if uid in self.peers:
                self.peers[uid].update({
                    "nick": nick, "ip": addr[0], "tcp_port": port,
                    "last_seen": now, "online": True,
                })
            else:
                old_uid = None
                for ouid, p in self.peers.items():
                    if p["nick"] == nick and not p["online"]:
                        old_uid = ouid
                        break
                if old_uid:
                    self.peers.pop(old_uid, None)
                self.peers[uid] = {
                    "nick": nick, "ip": addr[0], "tcp_port": port,
                    "last_seen": now, "online": True,
                }

        self._check_nick_conflict(uid, nick)
        self._publish_peers()

    def _check_nick_conflict(self, peer_uid, peer_nick):
        if self.nick_fixed or peer_nick != self.nick:
            return
        if self.uid < peer_uid:
            return
        self.nick = f"{self.base_nick}({self.uid[:4]})"
        self.nick_fixed = True
        self.q.put(("self_nick", self.nick))
        self.q.put(("notice", f"检测到重名，你的昵称已自动改为「{self.nick}」"))
        self._send_hello()

    def _publish_peers(self):
        with self.peers_lock:
            snap = {u: dict(p) for u, p in self.peers.items()}
        sig = tuple(sorted(
            (u, p["nick"], p["ip"], p["tcp_port"], p.get("online", False))
            for u, p in snap.items()))
        if sig != self._last_sig:
            self._last_sig = sig
            self.q.put(("peers", snap))

    def _send_hello(self):
        self._broadcast_udp({
            "magic": APP_MAGIC, "type": "hello",
            "uid": self.uid, "nick": self.nick,
            "tcp_port": self.tcp_port, "timestamp": time.time(),
        })

    def _broadcast_udp(self, obj):
        if not self.udp_sock:
            return
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        for tgt in self.broadcast_targets:
            try:
                self.udp_sock.sendto(data, (tgt, DISCOVERY_PORT))
            except OSError:
                pass

    def _heartbeat_loop(self):
        for _ in range(3):
            if not self.running:
                return
            self._send_hello()
            time.sleep(0.4)
        last = time.time()
        while self.running:
            time.sleep(0.5)
            if time.time() - last >= HEARTBEAT_INTERVAL:
                self._send_hello()
                last = time.time()

    def _cleanup_loop(self):
        while self.running:
            time.sleep(1.0)
            now = time.time()
            changed = False
            with self.peers_lock:
                for p in self.peers.values():
                    if p["online"] and now - p["last_seen"] > PEER_TIMEOUT:
                        p["online"] = False
                        changed = True
            if changed:
                self._publish_peers()

    def send_private(self, peer_uid, content, message_id):
        with self.peers_lock:
            peer = self.peers.get(peer_uid)
            if not peer:
                return False, "对方不在线"
            if not peer.get("online"):
                return False, "对方已离线"
            peer_snap = dict(peer)
        msg = {
            "type": "private_msg",
            "from": self.uid, "from_nick": self.nick,
            "from_ip": self.local_ip, "from_port": self.tcp_port,
            "to": peer_uid, "content": content,
            "timestamp": time.time(), "messageId": message_id,
        }
        for attempt in (1, 2):
            sock = self._get_send_socket(peer_uid, peer_snap)
            if sock is None:
                return False, "无法连接到对方（可能被防火墙拦截）"
            try:
                self._send_line(sock, msg)
                return True, None
            except OSError:
                self._drop_conn(sock)
                if attempt == 2:
                    return False, "消息发送失败"
        return False, "消息发送失败"

    def send_group(self, content):
        if len(content.encode("utf-8")) > 3000:
            content = content[:1000] + "…（消息过长已截断）"
        self._broadcast_udp({
            "magic": APP_MAGIC, "type": "group_msg",
            "from": self.uid, "from_nick": self.nick,
            "content": content, "timestamp": time.time(),
            "messageId": uuid.uuid4().hex,
        })
