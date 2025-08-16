# ADA Voice Assistant

このプロジェクトは、AI音声モデル「ADA」の音声合成機能とGoogle Geminiの強力なLLM（大規模言語モデル）を組み合わせたAIボイスアシスタントです。ウェブブラウザからテキストで質問すると、リアルタイムに音声で応答が返ってきます。

## 主な機能

  * **AI対話機能**: Google Gemini APIを利用した高度な対話AI。
  * **高品質なAI音声合成**: Fish Audio APIによる自然な日本語音声生成。
  * **リアルタイム通信**: `Flask-SocketIO`を用いた、ウェブブラウザとサーバー間の双方向リアルタイム通信。
  * **シンプルで軽量なフロントエンド**: HTML, CSS, JavaScriptのみで構築されたウェブインターフェース。
  * **自動デプロイ**: GitHub Actionsを利用したGitHub Pagesへの自動デプロイ。

## 技術スタック

  * **フロントエンド**:
      * HTML
      * CSS
      * JavaScript (Vanilla JS)
  * **バックエンド**:
      * Python 3.x
      * Flask
      * Flask-SocketIO
  * **API**:
      * Google Gemini API
      * Fish Audio API

## ファイル構造

```
.
├── .github/                # GitHub Actionsの設定ファイル
│   └── workflows/
│       └── deploy.yml      # GitHub Pagesへの自動デプロイ設定
├── backend/                # バックエンドのソースコード
│   ├── app.py              # Flaskサーバーのメインファイル
│   └── requirements.txt    # 必要なPythonライブラリの一覧
├── docs/                   # GitHub Pagesで公開されるウェブサイトのファイル
│   └── index.html          # ウェブサイトの本体（HTML/CSS/JSを含む）
└── README.md               # このドキュメント
```

## セットアップと実行方法

### 1\. リポジトリのクローン

```bash
git clone https://github.com/Ry02024/ada_voice_assistant.git
cd ada_voice_assistant
```

### 2\. バックエンドのセットアップ

`backend`ディレクトリに移動し、Pythonの仮想環境を作成・有効化して、必要なライブラリをインストールします。

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windowsの場合は venv\Scripts\activate
pip install -r requirements.txt
```

### 3\. 環境変数の設定

APIキーを安全に管理するため、`.env`ファイルを作成し、以下の情報を記述します。

```
GOOGLE_API_KEY="あなたのGoogle Gemini APIキー"
FISH_AUDIO_API_KEY="あなたのFish Audio APIキー"
```

### 4\. アプリケーションの実行

バックエンドサーバーを起動します。

```bash
python app.py
```

サーバーが起動したら、ウェブブラウザで`http://127.0.0.1:5000`にアクセスしてテストできます。

## デプロイ

このプロジェクトはGitHub Pagesを利用しており、`docs/`ディレクトリの内容が公開されます。
`deploy.yml`ファイルが、以下のプロセスを自動化しています。

1.  リポジトリへのプッシュを検知。
2.  `docs/`ディレクトリの内容をビルド。
3.  GitHub Pagesへデプロイ。

APIキーは、GitHubの**Secrets**に`GOOGLE_API_KEY`と`FISH_AUDIO_API_KEY`として設定することで、安全に扱われます。

-----
