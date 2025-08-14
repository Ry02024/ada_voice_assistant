import os
from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
import io
import requests
import re
import markdown
from google import genai
from dotenv import load_dotenv

# ローカルで実行する場合に .env ファイルを読み込む
load_dotenv()

app = Flask(__name__)
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
    gemini_client = genai.Client(api_key=GOOGLE_API_KEY)
except Exception as e:
    print("APIキー取得/クライアント初期化エラー:", e)
    gemini_client = None

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
    text = re.sub(r"```.*?```", "", md_text, flags=re.DOTALL)
    text = re.sub(r"^[\*\-\+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"`(.*?)`", r"\1", text)
    text = re.sub(r"^[#]+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"<[^>]+>", "", text)
    text = convert_times_for_speech(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def markdown_to_html(md_text: str) -> str:
    if not md_text:
        return ""
    try:
        return markdown.markdown(md_text, extensions=['nl2br'])
    except Exception:
        return "<pre>" + (md_text or "") + "</pre>"

# --------------------------
# Gemini 呼び出し
# --------------------------
def get_gemini_response(prompt_text: str):
    if not gemini_client:
        err_msg = "Geminiクライアントが初期化されていません。APIキーを確認してください。"
        return None, err_msg
    try:
        resp = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt_text,
        )
        md_text = getattr(resp, "text", "") or str(resp)
        html = markdown_to_html(md_text)
        plain = markdown_to_plaintext(md_text)
        return html, plain
    except Exception as e:
        return None, f"Gemini API エラー: {e}"

# --------------------------
# Fish Audio 呼び出し
# --------------------------
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
    d = request.get_json(force=True, silent=True) or {}
    prompt = d.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error":"プロンプトがありません"}), 400

    html, plain_or_error = get_gemini_response(prompt)
    if html is None:
        return jsonify({"error": plain_or_error}), 500

    return jsonify({"html": html, "plain": plain_or_error})

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