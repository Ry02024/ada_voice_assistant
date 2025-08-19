import os
import json
import re
import io
import requests
import markdown
import google.genai as genai
from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
from dotenv import load_dotenv

# ファイルからテキストを抽出するライブラリをインポート
from docx import Document
from PyPDF2 import PdfReader
import csv

# ローカルで実行する場合に .env ファイルを読み込む
load_dotenv()

# Flaskアプリケーションのインスタンス化
app = Flask(__name__, template_folder='templates')
CORS(app)

# --------------------------
# APIキー等の取得 & Gemini 初期化
# --------------------------
try:
    # Vercelやローカルの環境変数を読み込む
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
    FISH_AUDIO_TOKEN = os.environ.get('FISH_AUDIO_TOKEN')
    FISH_AUDIO_VOICE_ID = os.environ.get('FISH_AUDIO_VOICE_ID')
    # genai.Client 初期化
    genai_client = genai.Client(api_key=GOOGLE_API_KEY)
    print("Geminiクライアントを初期化しました。")
except Exception as e:
    print("APIキー取得/クライアント初期化エラー:", e)
    genai_client = None

# --------------------------
# ユーティリティ関数
# --------------------------
def convert_time_range(match):
    sh, sm, eh, em = match.groups()
    return f"{int(sh)}時{sm}分から{int(eh)}時{em}分"

def convert_single_time(match):
    h, m = match.groups()
    return f"{int(h)}時{m}分"

def convert_times_for_speech(text: str) -> str:
    text = re.sub(r"(\d{1,2}):(\d{2})\s*[-–〜~]\s*(\d{1,2}):(\d{2})", lambda m: convert_time_range(m), text)
    text = re.sub(r"(?<!\d)(\d{1,2}):(\d{2})(?!\d)", lambda m: convert_single_time(m), text)
    return text

def markdown_to_plaintext(md_text: str) -> str:
    if not md_text:
        return ""
    # コードブロックを削除
    text = re.sub(r"```.*?```", "", md_text, flags=re.DOTALL)
    # Markdown記号を削除
    text = re.sub(r"^[\*\-\+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"`(.*?)`", r"\1", text)
    text = re.sub(r"^[#]+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"<[^>]+>", "", text)
    text = convert_times_for_speech(text)
    # 連続する空白を1つにまとめる
    text = re.sub(r"\s+", " ", text).strip()
    return text

def markdown_to_html(md_text: str) -> str:
    if not md_text:
        return ""
    try:
        return markdown.markdown(md_text, extensions=['nl2br'])
    except Exception:
        return f"<pre>{md_text or ''}</pre>"

def extract_text_from_file(file_path, file_extension):
    """ファイルの拡張子に応じてテキストを抽出する"""
    text_content = ""
    if file_extension == ".txt":
        with open(file_path, 'r', encoding='utf-8') as f:
            text_content = f.read()
    elif file_extension == ".docx":
        doc = Document(file_path)
        text_content = "\n".join([paragraph.text for paragraph in doc.paragraphs])
    elif file_extension == ".pdf":
        with open(file_path, 'rb') as f:
            reader = PdfReader(f)
            for page in reader.pages:
                text_content += page.extract_text() or ""
    elif file_extension == ".csv":
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            text_content = "\n".join([",".join(row) for row in reader])
    else:
        raise ValueError(f"サポートされていないファイル形式です: {file_extension}")
    return text_content

def generate_personality_name(text_content):
    """Gemini API を使ってテキスト内容から人格名を生成する"""
    if not genai_client:
        return "新しいペルソナ"
    
    prompt_text = f"""
    以下のテキストコンテンツは、AI の人格設定（system instruction）です。
    この内容に最もふさわしい、簡潔でユニークな日本語の名前を1つだけ、名前の文字列のみで答えてください。
    説明や挨拶は含めないでください。例: '旅行ガイド', '歴史家アリス'

    テキストコンテンツ:
    「{text_content[:200]}...」
    """
    
    try:
        response = genai_client.models.generate_content(
            model="gemini-2.5-flash-lite-preview-06-17",
            contents=prompt_text
        )
        name = response.text.strip().replace('"', '')
        return name
    except Exception as e:
        print(f"人格名生成エラー: {e}")
        return "新しいペルソナ"

def get_ada_voice(text: str):
    if not FISH_AUDIO_TOKEN:
        print("Fish Audio token missing")
        return None
    API_URL = "https://api.fish.audio/v1/tts"
    headers = {
        "Authorization": f"Bearer {FISH_AUDIO_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {"reference_id": FISH_AUDIO_VOICE_ID, "text": text}
    try:
        r = requests.post(API_URL, headers=headers, json=data, timeout=30)
        r.raise_for_status()
        return r.content
    except Exception as e:
        print("Fish Audio API エラー:", e)
        return None

# --------------------------
# エンドポイント
# --------------------------
@app.route("/")
def index():
    return render_template('index.html')

@app.route("/api/chat", methods=['POST'])
def api_chat():
    if not genai_client:
        return jsonify({"error": "Geminiクライアントが初期化されていません。APIキーを確認してください。"}), 500

    d = request.get_json(force=True, silent=True) or {}
    prompt = d.get("prompt", "").strip()
    personality_name = d.get("personality", "デフォルト")
    
    if not prompt:
        return jsonify({"error":"プロンプトがありません"}), 400

@app.route("/api/tts", methods=['POST'])
def api_tts():
    d = request.get_json(force=True, silent=True) or {}
    text = d.get("text", "")
    if not text:
        return jsonify({"error":"テキストがありません"}), 400
    audio = get_ada_voice(text)
    if audio:
        return send_file(io.BytesIO(audio), mimetype="audio/mpeg")
    else:
        return jsonify({"error":"音声生成に失敗しました"}), 500

if __name__ == '__main__':
    # ローカル実行
    app.run(host='0.0.0.0', port=5000)
