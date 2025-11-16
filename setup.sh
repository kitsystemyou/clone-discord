#!/bin/bash

# 仮想環境の作成 (なければ)
uv venv

# 仮想環境をアクティベート
source .venv/bin/activate

# 必要なライブラリをインストール
uv pip install requests

echo "環境準備が完了しました。仮想環境がアクティベートされています。"