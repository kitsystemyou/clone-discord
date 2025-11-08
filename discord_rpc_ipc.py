import os
import sys
import json
import struct
import time
import uuid

# IPC通信に使うモジュールをOSによって切り替える
if sys.platform == 'win32':
    import win32pipe
    import win32file
    import pywintypes
else:
    import socket

# --- 設定 ---
# Discord Developer Portalで登録したアプリケーションのクライアントID
CLIENT_ID = os.getenv('CLIENT_ID')
# チャンネル一覧を取得したいサーバー（ギルド）のID
TARGET_GUILD_ID = os.getenv('TARGET_GUILD_ID')

# Discord RPCのパイプ名（Windows）またはソケットファイル名（Linux/macOS）のプレフィックス
PIPE_BASE = 'discord-ipc-'

# Discord RPCプロトコルのバージョン
RPC_VERSION = 1

if not (CLIENT_ID and TARGET_GUILD_ID):
    print("エラー: CLIENT_ID または TARGET_GUILD_ID の環境変数が設定されていません。")
    sys.exit(1)

# --- RPCメッセージのエンコード/デコード ---

def encode_message(opcode: int, data: dict) -> bytes:
    """RPCメッセージ（ヘッダーとペイロード）をバイト列にエンコードする"""
    payload = json.dumps(data).encode('utf-8')
    # ヘッダーは 4バイトのOpcode と 4バイトのペイロード長
    header = struct.pack('<II', opcode, len(payload))
    return header + payload

def decode_message(data: bytes) -> tuple[int, dict]:
    """バイト列からRPCメッセージ（ヘッダーとペイロード）をデコードする"""
    # 最初の8バイトがヘッダー (Opcode: 4バイト, Length: 4バイト)
    opcode, length = struct.unpack('<II', data[:8])
    payload = data[8:8 + length].decode('utf-8')
    return opcode, json.loads(payload)

# --- IPCソケットの接続と操作 ---

def get_ipc_path() -> str | None:
    """OSに応じてIPCソケット/パイプのパスを返す"""
    if sys.platform == 'win32':
        # Windowsでは名前付きパイプ
        return PIPE_BASE + '0' # 通常はパイプ0を使用
    
    # Linux/macOSではUnixソケット
    temp_dir = os.environ.get('XDG_RUNTIME_DIR') or os.environ.get('TMPDIR') or os.environ.get('TMP') or os.environ.get('TEMP') or '/tmp'
    
    # 0から9までのパイプを試す
    for i in range(10):
        path = os.path.join(temp_dir, PIPE_BASE + str(i))
        if os.path.exists(path):
            return path
    return None

def connect_ipc():
    """Discord RPCパイプ/ソケットに接続し、接続オブジェクトを返す"""
    path = get_ipc_path()
    if not path:
        print("エラー: Discord IPCソケット/パイプのパスが見つかりません。Discordクライアントが実行中か確認してください。")
        return None

    if sys.platform == 'win32':
        try:
            # Windows: 名前付きパイプに接続
            handle = win32file.CreateFile(
                r'\\.\pipe\\' + path,
                win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                0,
                None,
                win32file.OPEN_EXISTING,
                0,
                None
            )
            # パイプモードをメッセージモードに変更
            win32pipe.SetNamedPipeHandleState(handle, win32pipe.PIPE_READMODE_MESSAGE, None, None)
            return handle
        except pywintypes.error as e:
            print(f"Windowsパイプ接続エラー: {e}")
            return None
    else:
        # Linux/macOS: Unixソケットに接続
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.connect(path)
            return sock
        except FileNotFoundError:
            print(f"Unixソケット接続エラー: ファイルが見つかりません ({path})")
            return None
        except Exception as e:
            print(f"Unixソケット接続エラー: {e}")
            return None

def send_rpc_message(conn, opcode: int, data: dict):
    """RPCメッセージをソケット/パイプに送信する"""
    message = encode_message(opcode, data)
    if sys.platform == 'win32':
        # Windows: win32file.WriteFile
        win32file.WriteFile(conn, message)
    else:
        # Linux/macOS: socket.sendall
        conn.sendall(message)

def receive_rpc_message(conn) -> tuple[int, dict] | None:
    """RPCメッセージを受信する"""
    try:
        if sys.platform == 'win32':
            # Windows: win32file.ReadFile
            # ヘッダー (8バイト) を読み込む
            _, header_data = win32file.ReadFile(conn, 8)
        else:
            # Linux/macOS: socket.recv
            header_data = conn.recv(8)
        
        if len(header_data) < 8:
            return None # 接続が閉じられたか、データ不足

        opcode, length = struct.unpack('<II', header_data)
        
        if sys.platform == 'win32':
            # Windows: ペイロードを読み込む
            _, payload_data = win32file.ReadFile(conn, length)
        else:
            # Linux/macOS: ペイロードを読み込む
            payload_data = conn.recv(length)
        
        return opcode, json.loads(payload_data.decode('utf-8'))

    except Exception as e:
        # print(f"メッセージ受信エラー: {e}")
        return None

# --- RPCフローの実行 ---

def run_rpc_flow():
    """IPC接続からRPCコマンド実行までのメインフロー"""
    conn = connect_ipc()
    if not conn:
        return

    try:
        # 1. ハンドシェイク (Opcode 0: Handshake)
        print("1. ハンドシェイクの送信...")
        handshake_data = {"v": RPC_VERSION, "client_id": CLIENT_ID}
        send_rpc_message(conn, 0, handshake_data)

        # 2. ハンドシェイクの応答待ち
        response = receive_rpc_message(conn)
        if response is None or response[1].get('cmd') != 'DISPATCH':
            print("❌ ハンドシェイク応答エラー。DiscordクライアントのReady状態を確認してください。")
            return

        print(f"✅ ハンドシェイク成功。セッションID: {response[1].get('data', {}).get('session_id')}")

        # 3. 認証 (Opcode 1: Frame)
        # RPCコマンドを実行する前に、AUTHORIZE (Opcode 1) を実行する必要がありますが、
        # これはブラウザでのOAuth2.0フローを開始するため、IPC通信のみで完結しません。
        # 多くのRPCライブラリは、ローカルクライアントが既に認証済みであることを前提として進めます。
        
        # 4. GET_CHANNELS コマンドの送信 (Opcode 1: Frame)
        nonce = uuid.uuid4().hex
        get_channels_payload = {
            "cmd": "GET_CHANNELS",
            "args": {
                "guild_id": TARGET_GUILD_ID
            },
            "nonce": nonce
        }
        print(f"4. GET_CHANNELS コマンドの送信 (Nonce: {nonce})...")
        send_rpc_message(conn, 1, get_channels_payload)

        # 5. GET_CHANNELS の応答待ち
        # 最大5秒間、応答を待機する
        timeout = time.time() + 5
        while time.time() < timeout:
            response = receive_rpc_message(conn)
            if response is None:
                # 接続が切れた場合
                print("❌ 応答受信中に接続が切れました。")
                return

            opcode, data = response
            if data.get('nonce') == nonce and data.get('cmd') == 'GET_CHANNELS':
                print("\n--- チャンネル一覧の取得結果 ---")
                
                if data.get('evt') == 'ERROR':
                    # エラー応答
                    print(f"❌ RPCエラーが発生しました: {data.get('data', {}).get('message')}")
                    print("必要な権限がないか、RPCクライアントが認可されていません。")
                    return
                
                channels = data.get('data', [])
                for channel in channels:
                    channel_type = {0: 'TEXT', 2: 'VOICE', 4: 'CATEGORY'}.get(channel.get('type'), 'UNKNOWN')
                    print(f"[{channel_type:<10}] {channel.get('name')} (ID: {channel.get('id')})")
                print("--------------------------")
                return
            
            # その他のメッセージ (Rich Presenceの更新など) は無視して継続
            # print(f"他のメッセージを受信: {data.get('cmd')}")
            time.sleep(0.1)

        print("❌ 5秒以内に GET_CHANNELS の応答がありませんでした。")

    finally:
        # 接続をクローズ
        if sys.platform == 'win32':
            win32file.CloseHandle(conn)
        else:
            conn.close()
        print("IPC接続をクローズしました。")

if __name__ == '__main__':
    print("⚠️ 注意: このスクリプトの実行には、ローカルでPC版Discordクライアントが起動している必要があります。")
    run_rpc_flow()