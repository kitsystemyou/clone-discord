# clone-discord
clone discord: mainly channels, posts, attachments

## セットアップ

```bash
bash setup.sh
```

## 使用方法

### main.py - Discord Bot トークンを使用してチャンネルと投稿を取得

Discord Bot トークンを使用して、指定したサーバー（ギルド）のチャンネル一覧と各チャンネルの投稿を取得し、JSON ファイルに保存します。

#### 機能

- チャンネル一覧の取得と表示
- 各テキストチャンネルの投稿（メッセージ）を取得
- チャンネルごとに JSON ファイルに保存
- 投稿データには以下の情報を含む：
  - メッセージ内容
  - 投稿者情報
  - タイムスタンプ
  - 添付ファイル情報（URL、ファイル名、サイズ、コンテンツタイプ）
  - Embed 情報
  - リアクション情報
- サマリーファイル（`guild_summary.json`）の生成

#### 必要な環境変数

- `DISCORD_BOT_TOKEN`: Discord Bot のトークン
- `GUILD_ID`: チャンネル一覧を取得したいサーバー（ギルド）のID
- `OUTPUT_DIR`: 保存先ディレクトリ（デフォルト: `discord_data`）

#### 実行方法

```bash
export DISCORD_BOT_TOKEN="your_bot_token_here"
export GUILD_ID="your_guild_id_here"
export OUTPUT_DIR="discord_data"  # オプション
python3 main.py
```

#### 出力ファイル

実行すると、以下のファイルが生成されます：

```
discord_data/
├── guild_summary.json          # サーバー全体のサマリー
├── general_123456789.json      # 各チャンネルのデータ
├── announcements_987654321.json
└── ...
```

各チャンネルの JSON ファイルには以下の情報が含まれます：

```json
{
  "channel_id": "123456789",
  "channel_name": "general",
  "channel_type": 0,
  "message_count": 100,
  "fetched_at": "2024-01-01T00:00:00Z",
  "messages": [
    {
      "message_id": "987654321",
      "channel_id": "123456789",
      "channel_name": "general",
      "author": {
        "id": "111222333",
        "username": "user123",
        "bot": false
      },
      "content": "メッセージ内容",
      "timestamp": "2024-01-01T00:00:00Z",
      "attachments": [
        {
          "id": "444555666",
          "filename": "image.png",
          "size": 12345,
          "url": "https://cdn.discordapp.com/attachments/...",
          "content_type": "image/png"
        }
      ]
    }
  ]
}
```

#### Bot の準備

1. [Discord Developer Portal](https://discord.com/developers/applications) でアプリケーションを作成
2. Bot タブから Bot を作成し、トークンを取得
3. Bot に必要な権限を付与：
   - `View Channels` - チャンネル一覧の取得
   - `Read Message History` - 過去のメッセージの取得
4. OAuth2 URL Generator で Bot をサーバーに招待

#### 注意事項

- デフォルトでは各チャンネルから最大 100 件のメッセージを取得します
- レート制限を考慮して、リクエスト間に 0.5 秒の待機時間を設けています
- 添付ファイルの URL は保存されますが、ファイル本体のダウンロードは行いません
- アクセス権限のないチャンネルはスキップされます

### discord_rpc_ipc.py - Discord RPC を使用してチャンネル一覧を取得

Discord RPC (IPC) を使用して、ローカルで実行中の Discord クライアント経由でチャンネル一覧を取得します。

⚠️ **注意**: このスクリプトの実行には、ローカルで PC 版 Discord クライアントが起動している必要があります。

#### 必要な環境変数

- `CLIENT_ID`: Discord Developer Portal で登録したアプリケーションのクライアントID
- `TARGET_GUILD_ID`: チャンネル一覧を取得したいサーバー（ギルド）のID

#### 実行方法

```bash
export CLIENT_ID="your_client_id_here"
export TARGET_GUILD_ID="your_guild_id_here"
python3 discord_rpc_ipc.py
```
