import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path
import requests

BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
GUILD_ID = os.getenv('GUILD_ID')
OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'discord_data')

if not BOT_TOKEN:
    print("エラー: DISCORD_BOT_TOKEN 環境変数が設定されていません。")
    sys.exit(1)

if not GUILD_ID:
    print("エラー: GUILD_ID 環境変数が設定されていません。")
    sys.exit(1)

def get_guild_channels(guild_id: str) -> list:
    """指定されたギルド（サーバー）のチャンネル一覧を取得する"""
    url = f"https://discord.com/api/v10/guilds/{guild_id}/channels"
    headers = {
        "Authorization": f"Bot {BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            print("❌ 認証エラー: BOT_TOKENが無効です。")
        elif response.status_code == 403:
            print("❌ 権限エラー: ボットがこのサーバーにアクセスする権限がありません。")
        elif response.status_code == 404:
            print("❌ サーバーが見つかりません: GUILD_IDを確認してください。")
        else:
            print(f"❌ HTTPエラー: {e}")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"❌ リクエストエラー: {e}")
        sys.exit(1)

def get_channel_messages(channel_id: str, limit: int = 100) -> list:
    """指定されたチャンネルのメッセージ一覧を取得する"""
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {
        "Authorization": f"Bot {BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    
    all_messages = []
    last_message_id = None
    
    while True:
        params = {"limit": min(limit - len(all_messages), 100)}
        if last_message_id:
            params["before"] = last_message_id
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            messages = response.json()
            
            if not messages:
                break
            
            all_messages.extend(messages)
            last_message_id = messages[-1]['id']
            
            if len(all_messages) >= limit or len(messages) < 100:
                break
            
            time.sleep(0.5)
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 403:
                print(f"  ⚠️  チャンネル {channel_id} へのアクセス権限がありません")
                return []
            elif response.status_code == 404:
                print(f"  ⚠️  チャンネル {channel_id} が見つかりません")
                return []
            else:
                print(f"  ❌ HTTPエラー (チャンネル {channel_id}): {e}")
                return []
        except requests.exceptions.RequestException as e:
            print(f"  ❌ リクエストエラー (チャンネル {channel_id}): {e}")
            return []
    
    return all_messages

def process_message(message: dict, channel_id: str, channel_name: str) -> dict:
    """メッセージデータを処理して必要な情報を抽出する"""
    processed = {
        "message_id": message.get("id"),
        "channel_id": channel_id,
        "channel_name": channel_name,
        "author": {
            "id": message.get("author", {}).get("id"),
            "username": message.get("author", {}).get("username"),
            "discriminator": message.get("author", {}).get("discriminator"),
            "bot": message.get("author", {}).get("bot", False)
        },
        "content": message.get("content"),
        "timestamp": message.get("timestamp"),
        "edited_timestamp": message.get("edited_timestamp"),
        "attachments": [],
        "embeds": message.get("embeds", []),
        "reactions": message.get("reactions", [])
    }
    
    for attachment in message.get("attachments", []):
        processed["attachments"].append({
            "id": attachment.get("id"),
            "filename": attachment.get("filename"),
            "size": attachment.get("size"),
            "url": attachment.get("url"),
            "proxy_url": attachment.get("proxy_url"),
            "content_type": attachment.get("content_type")
        })
    
    return processed

def display_channels(channels: list):
    """チャンネル一覧を見やすく表示する"""
    channel_types = {
        0: 'TEXT',
        2: 'VOICE',
        4: 'CATEGORY',
        5: 'ANNOUNCEMENT',
        10: 'ANNOUNCEMENT_THREAD',
        11: 'PUBLIC_THREAD',
        12: 'PRIVATE_THREAD',
        13: 'STAGE_VOICE',
        15: 'FORUM',
        16: 'MEDIA'
    }
    
    print("\n--- チャンネル一覧 ---")
    for channel in channels:
        channel_type = channel_types.get(channel.get('type'), 'UNKNOWN')
        name = channel.get('name', '(名前なし)')
        channel_id = channel.get('id')
        position = channel.get('position', 0)
        parent_id = channel.get('parent_id', '')
        
        indent = "  " if parent_id else ""
        print(f"{indent}[{channel_type:<15}] {name:<30} (ID: {channel_id}, Position: {position})")
    print("----------------------\n")

def save_to_json(data: dict, filepath: Path):
    """データをJSONファイルに保存する"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fetch_and_save_channel_data(channel: dict, output_dir: Path):
    """チャンネルのデータを取得してJSONファイルに保存する"""
    channel_id = channel.get('id')
    channel_name = channel.get('name', 'unknown')
    channel_type = channel.get('type')
    
    text_channel_types = [0, 5, 10, 11, 12, 15]
    
    if channel_type not in text_channel_types:
        return None
    
    print(f"  チャンネル '{channel_name}' (ID: {channel_id}) のメッセージを取得中...")
    
    messages = get_channel_messages(channel_id)
    
    processed_messages = []
    for message in messages:
        processed_messages.append(process_message(message, channel_id, channel_name))
    
    channel_data = {
        "channel_id": channel_id,
        "channel_name": channel_name,
        "channel_type": channel_type,
        "parent_id": channel.get('parent_id'),
        "position": channel.get('position'),
        "topic": channel.get('topic'),
        "message_count": len(processed_messages),
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "messages": processed_messages
    }
    
    safe_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in channel_name)
    filename = f"{safe_name}_{channel_id}.json"
    filepath = output_dir / filename
    
    save_to_json(channel_data, filepath)
    print(f"  ✅ {len(processed_messages)} 件のメッセージを保存: {filepath}")
    
    return channel_data

if __name__ == '__main__':
    print(f"ギルドID {GUILD_ID} のチャンネル一覧を取得中...")
    channels = get_guild_channels(GUILD_ID)
    display_channels(channels)
    print(f"✅ 合計 {len(channels)} 個のチャンネルを取得しました。\n")
    
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"メッセージの取得を開始します (保存先: {output_path})...\n")
    
    guild_data = {
        "guild_id": GUILD_ID,
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "channels": []
    }
    
    for channel in channels:
        channel_summary = fetch_and_save_channel_data(channel, output_path)
        if channel_summary:
            guild_data["channels"].append({
                "channel_id": channel_summary["channel_id"],
                "channel_name": channel_summary["channel_name"],
                "channel_type": channel_summary["channel_type"],
                "message_count": channel_summary["message_count"]
            })
    
    summary_file = output_path / "guild_summary.json"
    save_to_json(guild_data, summary_file)
    print(f"\n✅ サマリーファイルを保存: {summary_file}")
    print(f"✅ 完了: {len(guild_data['channels'])} 個のチャンネルのデータを保存しました。")
