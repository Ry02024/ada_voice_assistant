import os
import json
import re
import io
import requests
import markdown
import vercel_blob
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
    BLOB_READ_WRITE_TOKEN = os.environ.get('BLOB_READ_WRITE_TOKEN')
    VERCEL_PROJECT_ID = os.environ.get('VERCEL_PROJECT_ID')

    # ↓↓↓ このあたりに追加してください ↓↓↓
    print("---------------------------------")
    print(f"BLOB_READ_WRITE_TOKEN が設定されています: {bool(BLOB_READ_WRITE_TOKEN)}")
    print(f"VERCEL_PROJECT_ID が設定されています: {bool(VERCEL_PROJECT_ID)}")
    print("---------------------------------")
    # ↑↑↑ ここまで ↑↑↑

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
        return f"<pre>{md_text or ''}</pre>"

def extract_text_from_file(file_path, file_extension):
    """ファイルの拡張子に応じてテキストを抽出する"""
    print(f"📄 ファイルからテキストを抽出中: {file_extension}")
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
    print("✅ テキスト抽出完了")
    return text_content

def generate_personality_name(text_content):
    """Gemini API を使ってテキスト内容から人格名を生成する"""
    print("🤖 Geminiでペルソナ名を生成中...")
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
        print(f"✅ ペルソナ名生成完了: {name}")
        return name
    except Exception as e:
        print(f"❌ 人格名生成エラー: {e}")
        return "新しいペルソナ"

# --------------------------
# Blob操作関数 (vercel_blob版)
# --------------------------
def save_personality_to_blob(text_content, user_defined_name=None):
    """人格設定をBlobにJSONとして保存する"""
    print("📤 Blobにデータをアップロード中...")
    
    if not BLOB_READ_WRITE_TOKEN:
        raise Exception("Vercel Blobトークンが設定されていません。")

    # `vercel_blob` ライブラリは環境変数からトークンを自動で読み込む
    # そのため、os.environ.get() で取得した値を直接使う必要はないですが、
    # 既存のコードのチェックは残しておきます。
    
    if user_defined_name:
        name = user_defined_name.replace(" ", "_").replace("/", "_")
    else:
        name = generate_personality_name(text_content).replace(" ", "_").replace("/", "_")
    
    # データを辞書として定義
    data = {"system_instruction": text_content}
    
    # JSONデータをUTF-8バイトにエンコード
    json_data_bytes = json.dumps(data, ensure_ascii=False).encode('utf-8')
    
    # ファイル名をユニークにするために addRandomSuffix を使用
    options = {"addRandomSuffix": "true"}
    
    try:
        # vercel_blob.put() を使用してアップロード
        # 第一引数にファイル名、第二引数にバイトデータを渡す
        response = vercel_blob.put(f"{name}.json", json_data_bytes, options)
        
        # 応答の検証はライブラリが内部で行う
        uploaded_url = response['url']
        print(f"✅ ペルソナ '{name}' をBlobに保存しました。URL: {uploaded_url}")
        return name
        
    except Exception as e:
        print(f"❌ Blobへの保存中にエラーが発生しました: {e}")
        raise Exception(f"Blobへの保存中にエラーが発生しました: {e}")


def load_personalities_from_blob():
    """Blobからすべての人格を読み込む"""
    print("📥 Blobからデータをダウンロード中...")
    personalities = {}
    
    # vercel_blob.list() を使用してファイルの一覧を取得
    try:
        # `vercel_blob` は環境変数を自動で読み込む
        list_response = vercel_blob.list()
        files = list_response.get('blobs', [])

        for file in files:
            if file['pathname'].endswith('.json'):
                # `vercel_blob` には download_file があるが、ここでは直接URLにrequestsを使う
                # requestsを使った既存のコードを流用
                blob_url = file['url']
                headers = {"Authorization": f"Bearer {BLOB_READ_WRITE_TOKEN}"}
                file_response = requests.get(blob_url, headers=headers)
                
                if file_response.status_code == 200:
                    try:
                        data = file_response.json()
                        name = os.path.splitext(file['pathname'])[0]
                        
                        # ランダムなサフィックスを削除
                        clean_name = re.sub(r'_[a-f0-9]{8}$', '', name)
                        personalities[clean_name] = data.get("system_instruction", "")
                        
                    except json.JSONDecodeError:
                        print(f"❌ JSONデコードエラー: {file['pathname']}")
                        continue
        print("✅ Blobからペルソナを読み込みました。")
    except Exception as e:
        print(f"❌ Blobからの読み込み中にエラーが発生しました: {e}")
        return {}
    return personalities

def load_personalities():
    """環境に応じてBlobまたはローカルディレクトリから人格を読み込む"""
    print("🔄 ペルソナをロード中...")
    if BLOB_READ_WRITE_TOKEN and VERCEL_PROJECT_ID:
        print("Blobからペルソナを読み込みます。")
        return load_personalities_from_blob()
    else:
        print("ローカルからペルソナを読み込みます。")
        personalities = {}
        personalities_dir = 'personalities'
        if not os.path.exists(personalities_dir):
            os.makedirs(personalities_dir)
            return personalities
        
        for filename in os.listdir(personalities_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(personalities_dir, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        name = os.path.splitext(filename)[0]
                        personalities[name] = data.get("system_instruction", "")
                except Exception as e:
                    print(f"❌ 人格ファイル '{filename}' の読み込みエラー: {e}")
        return personalities

def save_personality(text_content, user_defined_name=None):
    """環境に応じてBlobまたはローカルディレクトリに人格を保存する"""
    print("📝 ペルソナを保存中...")
    if BLOB_READ_WRITE_TOKEN and VERCEL_PROJECT_ID:
        print("Blobにペルソナを保存します。")
        return save_personality_to_blob(text_content, user_defined_name)
    else:
        print("ローカルにペルソナを保存します。")
        personalities_dir = 'personalities'
        if not os.path.exists(personalities_dir):
            os.makedirs(personalities_dir)
        
        if user_defined_name:
            name = user_defined_name.replace(" ", "_").replace("/", "_")
        else:
            name = generate_personality_name(text_content).replace(" ", "_").replace("/", "_")
        
        file_path = os.path.join(personalities_dir, f"{name}.json")
        
        data = {"system_instruction": text_content}
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
        return name

# --------------------------
# Fish Audio 呼び出し
# --------------------------
def get_ada_voice(text: str):
    print("🎤 音声生成を開始します...")
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
        print("✅ 音声生成完了")
        return r.content
    except Exception as e:
        print("❌ Fish Audio API エラー:", e)
        return None

# --------------------------
# エンドポイント
# --------------------------
@app.route("/")
def index():
    print("🌐 indexページにアクセスされました。")
    return render_template('index.html')

@app.route("/api/personalities", methods=['GET'])
def list_personalities():
    print("📝 /api/personalities がリクエストされました。")
    personalities = load_personalities()
    return jsonify({"personalities": list(personalities.keys())})

@app.route("/api/chat", methods=['POST'])
def api_chat():
    print("💬 /api/chat がリクエストされました。")
    if not genai_client:
        return jsonify({"error": "Geminiクライアントが初期化されていません。APIキーを確認してください。"}), 500

    d = request.get_json(force=True, silent=True) or {}
    prompt = d.get("prompt", "").strip()
    personality_name = d.get("personality", "デフォルト")
    
    if not prompt:
        return jsonify({"error":"プロンプトがありません"}), 400

    print(f"🤖 ペルソナ '{personality_name}' でチャットを生成中...")
    # 選択されたペルソナを読み込む
    personalities = load_personalities()
    system_instruction = personalities.get(personality_name, "あなたは親切なアシスタントです。")
    
    # system_instructionをユーザープロンプトに統合
    full_prompt = f"{system_instruction}\n\nユーザー入力: {prompt}"
    
    try:
        response = genai_client.models.generate_content(
            model="gemini-2.5-flash-lite-preview-06-17",
            contents=full_prompt
        )
        md_text = getattr(response, "text", "") or str(response)
        html = markdown_to_html(md_text)
        plain = markdown_to_plaintext(md_text)
        print("✅ チャット応答生成完了。")
        return jsonify({"html": html, "plain": plain})
    except Exception as e:
        print("❌ Gemini API エラー:", e)
        return jsonify({"error": f"Gemini API エラー: {e}"}), 500

@app.route("/api/tts", methods=['POST'])
def api_tts():
    print("🔊 /api/tts がリクエストされました。")
    d = request.get_json(force=True, silent=True) or {}
    text = d.get("text", "")
    if not text:
        return jsonify({"error":"テキストがありません"}), 400
    audio = get_ada_voice(text)
    if audio:
        return send_file(io.BytesIO(audio), mimetype="audio/mpeg")
    else:
        return jsonify({"error":"音声生成に失敗しました"}), 500

@app.route("/api/personalities/add", methods=['POST'])
def add_personality():
    print("➕ /api/personalities/add がリクエストされました。")
    if 'file' not in request.files and 'text_content' not in request.form:
        return jsonify({"error": "ファイルまたはテキストが提供されていません。"}), 400

    text_content = request.form.get('text_content', '')
    user_defined_name = request.form.get('name', None)

    if 'file' in request.files:
        file = request.files['file']
        filename, file_extension = os.path.splitext(file.filename)
        
        # ファイルを一時的に保存
        temp_path = os.path.join(app.root_path, "temp_file" + file_extension)
        file.save(temp_path)
        
        try:
            text_content = extract_text_from_file(temp_path, file_extension)
        except ValueError as e:
            os.remove(temp_path)
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            os.remove(temp_path)
            return jsonify({"error": f"ファイルの読み込み中にエラーが発生しました: {e}"}), 500
        finally:
            os.remove(temp_path) # 一時ファイルを削除

    if not text_content:
        return jsonify({"error": "抽出されたテキストが空です。"}), 400

    try:
        new_name = save_personality(text_content, user_defined_name)
        print("✅ ペルソナ追加処理完了。")
        return jsonify({"message": f"新しいペルソナ '{new_name}' を追加しました。"})
    except Exception as e:
        print("❌ ペルソナ追加処理中にエラーが発生しました。")
        return jsonify({"error": f"ペルソナの保存中にエラーが発生しました: {e}"}), 500

if __name__ == '__main__':
    # ローカル実行
    app.run(host='0.0.0.0', port=5000)