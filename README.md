# ada_voice_assistant

## 概要

`ada_voice_assistant` は、Google Geminiの強力なLLM（大規模言語モデル）とFish Audioの高品質なAI音声合成（Text-to-Speech, TTS）を組み合わせた、先進的なAIアシスタントです。本プロジェクトは、会話AI、音声認識、リアルタイムの音声ストリーミング、さらにはカメラからの映像入力にも対応し、多岐にわたるタスクをこなすことができます。

このアプリケーションは、Python（Flask）をバックエンド、Reactをフロントエンドとして構築されており、Vercelのサーバーレスプラットフォームにデプロイすることで、スケーラブルかつ効率的な運用を実現しています。

## 特徴

  - **対話型AI**: Google Gemini APIを活用し、自然で流暢な会話が可能です。
  - **リアルタイム音声合成**: Fish AudioのAPIを通じて、AIの応答を高品質な音声でストリーミングします。
  - **多モーダル入力**: テキスト、音声、さらにはウェブカメラからの映像フレーム[1]を処理し、より豊かな対話体験を提供します。
  - **効率的なデプロイ**: Vercelに最適化されており、Gitリポジトリへのプッシュによって自動的にデプロイされます。

## 技術スタック

  - **フロントエンド**: React
  - **バックエンド**: Python (Flask, SocketIO)
  - **AI/LLM**: Google Gemini API
  - **音声合成**: Fish Audio API
  - **デプロイ**: Vercel

## 環境構築

このプロジェクトをローカルで実行するには、以下の手順に従ってください。

### 前提条件

  - Python (3.x)
  - Node.js および npm
  - Git

### 1\. リポジトリをクローンする

```bash
git clone https://github.com/LOU-Ark/ada_voice_assistant.git
cd ada_voice_assistant
```

### 2\. バックエンドのセットアップ

`backend` ディレクトリに移動し、Pythonの仮想環境をセットアップして依存関係をインストールします[1]。

```bash
cd backend
python -m venv venv
# Windows:
# venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate
pip install -r requirements.txt
```

### 3\. フロントエンドのセットアップ

`frontend` ディレクトリに移動し、依存関係をインストールします[1]。

```bash
cd../frontend
npm install
```

### 4\. 環境変数の設定

APIキーなどの機密情報は、ソースコードに直接記述せず、環境変数として管理することが非常に重要です。プロジェクトのルートディレクトリに`.env`ファイルを作成し、必要なキーを以下のように記述してください[1, 2]。

```ini
#.env ファイル
FISH_AUDIO_API_KEY=YOUR_FISH_AUDIO_API_KEY_HERE
GOOGLE_API_KEY=YOUR_GOOGLE_AI_STUDIO_KEY_HERE
MAPS_API_KEY=YOUR_GOOGLE_MAPS_API_KEY_HERE
FLASK_SECRET_KEY=YOUR_RANDOM_SECRET_KEY_HERE
```

  - **`FISH_AUDIO_API_KEY`**: Fish AudioのAPIキー。Fish Audioのウェブサイトから取得できます[3]。
  - **`GOOGLE_API_KEY`**: Google Gemini APIのキー。Google AI Studioで作成します[2]。
  - **`MAPS_API_KEY`**: Google Maps Platformのキー。Google Cloud Consoleでプロジェクトを作成し、Directions APIを有効にして取得します[2]。
  - **`FLASK_SECRET_KEY`**: Flaskアプリケーションのセッション管理に使用されるランダムなシークレットキー[1]。

> **注意**: `.env`ファイルはGitにコミットしないように、`.gitignore`に必ず追加してください[1]。

### 5\. アプリケーションの実行

ローカル環境でアプリケーションを起動するには、バックエンドとフロントエンドをそれぞれ別のターミナルで実行する必要があります[1]。

**ターミナル1（バックエンド）**:

```bash
cd backend
# 仮想環境をアクティベート
python app.py
```

**ターミナル2（フロントエンド）**:

```bash
cd frontend
npm start
```

## Vercelへのデプロイ

VercelとGitHubを連携させることで、デプロイプロセスを自動化できます。

1.  **GitHubリポジトリをVercelにインポート**: Vercelダッシュボードの「Add New Project」から、本GitHubリポジトリをインポートします[4, 5]。
2.  **環境変数を設定**: プロジェクト設定の「Environment Variables」セクションで、上記で設定したキーと値を登録します[4, 6, 7]。
3.  **デプロイ**: Vercelは、リポジトリにプッシュされた変更を自動的に検出し、デプロイを開始します[4]。

Vercelのサーバーレス機能は、AIモデルの応答ストリーミングのようなI/O集約型タスクにも最適化されており、効率的な処理を実現します[8]。

## コストに関する情報

このプロジェクトでは、Vercelのホビーティアを含む多くのサービスを無料で利用できます。ただし、Fish Audio APIには無料ティアが提供されていますが、使用量やより高度な機能（高音質音声など）に応じてコストが発生する可能性があります[9, 10]。

## ライセンス

(ライセンス情報を追記してください)
