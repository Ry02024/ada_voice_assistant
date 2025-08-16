# ADA Voice Assistant

このプロジェクトは、AI音声モデル「ADA」の音声合成機能とGoogle Geminiの強力なLLM（大規模言語モデル）を組み合わせたAIボイスアシスタントです。ウェブブラウザからテキストで質問すると、リアルタイムに音声で応答が返ってきます。

## 主な機能

*   **AI対話機能**: Google Gemini APIを利用した高度な対話AI。
*   **高品質なAI音声合成**: Fish Audio APIによる自然な日本語音声生成。
*   **シンプルなWebインターフェース**: HTML, CSS, JavaScriptのみで構築された、軽量なシングルページのウェブインターフェース。
*   **Vercelへのデプロイ対応**: サーバーレスアーキテクチャで簡単にデプロイ可能。

## 技術スタック

*   **フロントエンド**:
    *   HTML
    *   CSS
    *   JavaScript (Vanilla JS)
*   **バックエンド**:
    *   Python 3.x
    *   Flask
*   **API**:
    *   Google Gemini API
    *   Fish Audio API
*   **デプロイメント**:
    *   Vercel

## ファイル構造

```
.
├── api/
│   ├── index.py              # Flaskサーバーのメインファイル
│   └── templates/
│       └── index.html      # ウェブサイトの本体（HTML/CSS/JSを含む）
├── requirements.txt        # 必要なPythonライブラリの一覧
├── vercel.json             # Vercelデプロイ設定ファイル
└── README.md               # このドキュメント
```

## セットアップとローカルでの実行方法

### 1. リポジトリのクローン

```bash
git clone https://github.com/Ry02024/ada_voice_assistant.git
cd ada_voice_assistant
```

### 2. Python仮想環境とライブラリのインストール

Pythonの仮想環境を作成・有効化して、必要なライブラリをインストールします。

```bash
python -m venv venv
source venv/bin/activate  # Windowsの場合は venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 環境変数の設定

APIキーを安全に管理するため、プロジェクトのルートディレクトリに`.env`ファイルを作成し、以下の情報を記述します。

```
GOOGLE_API_KEY="あなたのGoogle Gemini APIキー"
FISH_AUDIO_TOKEN="あなたのFish Audio APIトークン"
FISH_AUDIO_VOICE_ID="あなたのFish Audioの音声ID"
```

### 4. アプリケーションの実行

バックエンドサーバーを起動します。

```bash
python api/index.py
```

サーバーが起動したら、コンソールに表示されるURL（通常は `http://127.0.0.1:5000`）にウェブブラウザでアクセスして動作を確認できます。

## デプロイ

このプロジェクトはVercelへのデプロイを前提として構成されています。

1.  Vercel CLIをインストールします。
2.  `vercel login`でログインします。
3.  プロジェクトのルートで`vercel`コマンドを実行してデプロイします。

APIキーなどの環境変数は、Vercelプロジェクトの「Settings」>「Environment Variables」で設定してください。

```
GOOGLE_API_KEY
FISH_AUDIO_TOKEN
FISH_AUDIO_VOICE_ID
```
