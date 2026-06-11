import os
import json
import re
import io
import requests
import markdown
try:
    import vercel_blob # vercel_blobライブラリは環境変数からトークンを自動で読み込む
except Exception:
    vercel_blob = None
from docx import Document
from PyPDF2 import PdfReader
import csv
from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
import google.genai as genai

# ローカルで実行する場合に .env ファイルを読み込む
load_dotenv()

# Flaskアプリケーションのインスタンス化
# template_folder と static_folder を api フォルダ内に指定
app = Flask(__name__, template_folder='templates', static_folder='static')
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
    GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-3.5-flash')

    print("---------------------------------")
    print(f"BLOB_READ_WRITE_TOKEN が設定されています: {bool(BLOB_READ_WRITE_TOKEN)}")
    print(f"VERCEL_PROJECT_ID が設定されています: {bool(VERCEL_PROJECT_ID)}")
    print(f"GOOGLE_API_KEY が設定されています: {bool(GOOGLE_API_KEY)}")
    print(f"GEMINI_MODEL: {GEMINI_MODEL}")
    print("---------------------------------")

    # genai.Client 初期化 (APIキーがある場合のみ)
    genai_client = None
    if GOOGLE_API_KEY:
        genai_client = genai.Client(api_key=GOOGLE_API_KEY)
        print("Geminiクライアントを初期化しました。")
    else:
        print("警告: GOOGLE_API_KEY が設定されていません。Gemini機能は利用できません。")

except Exception as e:
    print(f"APIキー取得/クライアント初期化エラー: {e}")
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
    """音声合成用に時刻表記を変換する"""
    # 例: "10:30-11:00" -> "10時30分から11時00分"
    text = re.sub(r"(\d{1,2}):(\d{2})\s*[-–〜~]\s*(\d{1,2}):(\d{2})", lambda m: convert_time_range(m), text)
    # 例: "14:00" -> "14時00分"
    text = re.sub(r"(?<!\d)(\d{1,2}):(\d{2})(?!\d)", lambda m: convert_single_time(m), text)
    return text

def markdown_to_plaintext(md_text: str) -> str:
    """Markdownテキストをプレーンテキストに変換し、音声合成に適した形にする"""
    if not md_text:
        return ""
    
    # Markdownの基本的な要素を削除 (コードブロック、リスト、太字、斜体など)
    text = re.sub(r'`(.*?)`', r'\1', md_text, flags=re.DOTALL) # インラインコード
    text = re.sub(r'```.*?```', '', md_text, flags=re.DOTALL) # コードブロック
    text = re.sub(r'^[*-+]\s+', '', text, flags=re.MULTILINE) # リスト項目
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text) # 太字
    text = re.sub(r'\*(.*?)\*', r'\1', text) # 斜体
    text = re.sub(r'__\s*(.*?)\s*__', r'\1', text) # 下線付き太字
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'\1', text) # リンク (テキストのみ)
    text = re.sub(r'^[#]+\s*', '', text, flags=re.MULTILINE) # 見出し
    text = re.sub(r'<[^>]+>', '', text) # HTMLタグ
    
    # 時刻表記を音声合成用に変換
    text = convert_times_for_speech(text)
    
    # 連続する空白文字を1つにまとめる
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def markdown_to_html(md_text: str) -> str:
    """MarkdownテキストをHTMLに変換する"""
    if not md_text:
        return ""
    try:
        # nl2br拡張で改行を<br>に変換
        return markdown.markdown(md_text, extensions=['nl2br'])
    except Exception:
        # エラー時はプレーンテキストとして表示
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
        print("Geminiクライアントがないため、デフォルト名を使用します。")
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
            model=GEMINI_MODEL, # または他の適切なモデル
            contents=prompt_text
        )
        # response.text が存在しない場合のフォールバック
        name = getattr(response, 'text', '').strip().replace('"', '')
        if not name: # response.text が空の場合
             print("Geminiからの応答が空でした。デフォルト名を使用します。")
             return "新しいペルソナ"

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
    if not BLOB_READ_WRITE_TOKEN or not VERCEL_PROJECT_ID:
        raise Exception("Vercel BlobトークンまたはプロジェクトIDが設定されていません。")

    if vercel_blob is None:
        raise Exception("vercel_blob ライブラリがインストールされていません。pip install vercel-blob を検討してください。")

    # ペルソナ名を決定
    if user_defined_name:
        name = user_defined_name.replace(" ", "_").replace("/", "_")
    else:
        name = generate_personality_name(text_content).replace(" ", "_").replace("/", "_")
    
    # ファイル名をユニークにするために addRandomSuffix を使用
    options = {"addRandomSuffix": "true"}
    
    # データを辞書として定義 (system_instruction キーを使用)
    data = {"system_instruction": text_content}
    
    # JSONデータをUTF-8バイトにエンコード
    json_data_bytes = json.dumps(data, ensure_ascii=False, indent=4).encode('utf-8')

    try:
        # vercel_blob.put() を使用してアップロード
        # 第一引数: ファイルパス (例: "personality_name.json")
        # 第二引数: ファイルデータ (バイト列)
        # options: アップロードオプション
        response = vercel_blob.put(f"{name}.json", json_data_bytes, options)
        
        uploaded_url = response.get('url')
        print(f"✅ ペルソナ '{name}' をBlobに保存しました。URL: {uploaded_url}")
        return name
        
    except Exception as e:
        print(f"❌ Blobへの保存中にエラーが発生しました: {e}")
        raise Exception(f"Blobへの保存中にエラーが発生しました: {e}")

def load_personalities_from_blob():
    """Blobからすべての人格を読み込む"""
    print("📥 Blobからデータをダウンロード中...")
    personalities = {}
    if not BLOB_READ_WRITE_TOKEN:
        print("Blobトークンがないため、Blobからの読み込みはスキップします。")
        return personalities # 空の辞書を返す

    try:
        # vercel_blob.list() でファイル一覧を取得
        list_response = vercel_blob.list()
        files = list_response.get('blobs', [])

        for file in files:
            if file.get('pathname', '').endswith('.json'):
                blob_url = file.get('url')
                if not blob_url:
                    print(f"❌ URLが見つかりません: {file.get('pathname')}")
                    continue

                # Blob URLから直接データを取得 (requestsを使用)
                # Vercel Blob のURLは認証なしでアクセスできる場合が多いが、
                # セキュリティのためトークンが必要な場合もある (ここではrequestsで試行)
                try:
                    # Blob URLに直接アクセスしてファイル内容を取得
                    file_response = requests.get(blob_url, timeout=10) # タイムアウトを設定
                    file_response.raise_for_status() # エラーチェック
                    
                    data = file_response.json()
                    
                    # ファイル名から拡張子を除去し、ランダムサフィックスを削除
                    pathname = file['pathname']
                    name_with_suffix = os.path.basename(pathname) # 例: "my_persona_a1b2c3d4.json"
                    name_without_ext = os.path.splitext(name_with_suffix)[0] # 例: "my_persona_a1b2c3d4"
                    
                    # 末尾のランダムサフィックス (例: _a1b2c3d4) を削除
                    clean_name = re.sub(r'_[a-f0-9]{8}$', '', name_without_ext)
                    
                    personalities[clean_name] = data.get("system_instruction", "")
                    
                except requests.exceptions.RequestException as req_err:
                    print(f"❌ ファイル取得エラー ({blob_url}): {req_err}")
                except json.JSONDecodeError:
                    print(f"❌ JSONデコードエラー: {pathname}")
                except Exception as e:
                    print(f"❌ ファイル処理中に予期せぬエラー: {pathname} - {e}")
                    
        print(f"✅ Blobから {len(personalities)} 件のペルソナを読み込みました。")
    except Exception as e:
        print(f"❌ Blobからのファイル一覧取得中にエラーが発生しました: {e}")
        # エラーが発生しても、ローカルファイルからの読み込みは試行する
    return personalities

def load_personalities():
    """環境に応じてBlobまたはローカルディレクトリから人格を読み込む"""
    print("🔄 ペルソナをロード中...")
    personalities = {}
    
    # Vercel Blobが利用可能な場合、まずBlobから読み込む
    if BLOB_READ_WRITE_TOKEN and VERCEL_PROJECT_ID:
        print("Blobからペルソナを読み込みます。")
        try:
            personalities = load_personalities_from_blob()
            if personalities: # Blobから読み込めた場合
                return personalities
            else:
                print("Blobからペルソナが見つかりませんでした。ローカルディレクトリを検索します。")
        except Exception as e:
            print(f"Blobからの読み込み中にエラーが発生しました: {e}。ローカルディレクトリを検索します。")

    # Blobから読み込めなかった場合、またはBlobが利用できない場合はローカルディレクトリを検索
    print("ローカルディレクトリからペルソナを読み込みます。")
    personalities_dir = 'personalities'
    if not os.path.exists(personalities_dir):
        os.makedirs(personalities_dir) # ディレクトリが存在しない場合は作成
        print(f"'{personalities_dir}' ディレクトリを作成しました。")

    for filename in os.listdir(personalities_dir):
        if filename.endswith('.json'):
            file_path = os.path.join(personalities_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    name = os.path.splitext(filename)[0] # ファイル名から拡張子を除去
                    personalities[name] = data.get("system_instruction", "")
            except Exception as e:
                print(f"❌ 人格ファイル '{filename}' の読み込みエラー: {e}")
    
    if not personalities:
        print("ローカルディレクトリにペルソナファイルが見つかりませんでした。")

    return personalities

def save_personality(text_content, user_defined_name=None):
    """環境に応じてBlobまたはローカルディレクトリに人格を保存する"""
    print("📝 ペルソナを保存中...")
    
    # Vercel Blobが利用可能な場合、Blobに保存する
    if BLOB_READ_WRITE_TOKEN and VERCEL_PROJECT_ID:
        print("Blobにペルソナを保存します。")
        try:
            return save_personality_to_blob(text_content, user_defined_name)
        except Exception as e:
            print(f"Blobへの保存に失敗しました: {e}。ローカルに保存を試みます。")
            # Blob保存失敗時でもローカル保存は試みる
            pass # fallback to local save

    # Blobが利用できない、または保存に失敗した場合はローカルディレクトリに保存
    print("ローカルディレクトリにペルソナを保存します。")
    personalities_dir = 'personalities'
    if not os.path.exists(personalities_dir):
        os.makedirs(personalities_dir)
        print(f"'{personalities_dir}' ディレクトリを作成しました。")

    # ペルソナ名を決定
    if user_defined_name:
        name = user_defined_name.replace(" ", "_").replace("/", "_")
    else:
        name = generate_personality_name(text_content).replace(" ", "_").replace("/", "_")
    
    file_path = os.path.join(personalities_dir, f"{name}.json")
    
    data = {"system_instruction": text_content}
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"✅ ペルソナ '{name}' をローカルに保存しました。")
        return name
    except Exception as e:
        print(f"❌ ローカルへの保存中にエラーが発生しました: {e}")
        raise Exception(f"ローカルへの保存中にエラーが発生しました: {e}")

# --------------------------
# Fish Audio 呼び出し
# --------------------------

def get_ada_voice(text: str):
    """Fish Audio API を使用して音声を生成する"""
    print("🎤 音声生成を開始します...")
    if not FISH_AUDIO_TOKEN:
        print("Fish Audio token が設定されていません。")
        return None
    
    API_URL = "https://api.fish.audio/v1/tts"
    headers = {
        "Authorization": f"Bearer {FISH_AUDIO_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {"reference_id": FISH_AUDIO_VOICE_ID, "text": text}
    
    try:
        r = requests.post(API_URL, headers=headers, json=data, timeout=30) # タイムアウトを設定
        r.raise_for_status() # HTTPエラーチェック
        print("✅ 音声生成完了")
        return r.content # 音声データをバイト列で返す
    except requests.exceptions.RequestException as e:
        print(f"❌ Fish Audio API エラー: {e}")
        return None
    except Exception as e:
        print(f"❌ 音声生成中に予期せぬエラー: {e}")
        return None

# --------------------------
# エンドポイント
# --------------------------

@app.route("/")
def index():
    """メインページを表示"""
    print("🌐 indexページにアクセスされました。")
    # template_folder="templates" の設定により、templates/index.html をレンダリング
    return render_template('index.html')

@app.route("/api/personalities/<name>", methods=['GET'])
def get_personality(name):
    """指定されたペルソナのデータを返す"""
    print(f"👤 /api/personalities/{name} がリクエストされました。")
    personalities = load_personalities()
    if name in personalities:
        return jsonify({"name": name, "system_instruction": personalities[name]})
    else:
        return jsonify({"error": f"ペルソナ '{name}' が見つかりません。"}), 404


@app.route("/api/personalities", methods=['GET'])
def list_personalities():
    """登録されているペルソナ名の一覧を返すエンドポイント。
    フロントエンドはこのエンドポイントを呼んでセレクトボックスを構築します。
    """
    try:
        personalities = load_personalities()
        # personalities は { name: system_instruction } 形式の辞書
        names = list(personalities.keys())
        return jsonify({"personalities": names})
    except Exception as e:
        print(f"❌ ペルソナ一覧取得エラー: {e}")
        return jsonify({"personalities": []}), 500

def update_personality_local(name, text_content):
    personalities_dir = 'personalities'
    if not os.path.exists(personalities_dir):
        os.makedirs(personalities_dir)

    file_path = os.path.join(personalities_dir, f"{name}.json")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"ペルソナ '{name}' が見つかりません。")

    data = {"system_instruction": text_content}
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    return name
    
@app.route("/api/personalities/update", methods=['POST'])
def update_personality():
    """既存のペルソナを更新する"""
    print("🔄 /api/personalities/update がリクエストされました。")

    d = request.get_json(force=True, silent=True) or {}
    name = d.get("name", "").strip()
    text_content = d.get("text_content", "").strip()

    if not name:
        return jsonify({"error": "name が空です。"}), 400

    if not text_content:
        return jsonify({"error": "text_content が空です。"}), 400

    personalities = load_personalities()
    if name not in personalities:
        return jsonify({"error": f"ペルソナ '{name}' が見つかりません。"}), 404

    try:
        update_personality_local(name, text_content)
        return jsonify({
            "message": f"ペルソナ '{name}' を更新しました。",
            "name": name
        }), 200
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        print(f"❌ ペルソナ更新エラー: {e}")
        return jsonify({"error": f"更新中にエラーが発生しました: {e}"}), 500    

@app.route("/api/chat", methods=['POST'])
def api_chat():
    """ユーザーのプロンプトに対するGeminiの応答を生成する"""
    print("💬 /api/chat がリクエストされました。")
    if not genai_client:
        return jsonify({"error": "Geminiクライアントが初期化されていません。APIキーを確認してください。"}), 500

    # JSONリクエストボディを取得、失敗した場合は空の辞書を返す
    d = request.get_json(force=True, silent=True) or {}
    prompt = d.get("prompt", "").strip()
    personality_name = d.get("personality", "Default Assistant") # デフォルト値

    if not prompt:
        return jsonify({"error": "プロンプトが空です。"}), 400

    print(f"🤖 ペルソナ '{personality_name}' でチャットを生成中...")
    
    # 選択されたペルソナのシステム命令を読み込む
    personalities = load_personalities()
    system_instruction = personalities.get(personality_name, "あなたは親切なアシスタントです。") # デフォルトの指示

    # システム命令とユーザープロンプトを結合
    full_prompt = f"{system_instruction}\n\nユーザー入力: {prompt}"

    try:
        # Gemini API にリクエストを送信
        response = genai_client.models.generate_content(
            model="gemini-2.5-flash-lite-preview-06-17", # 使用するモデルを指定
            contents=full_prompt
        )
        # 応答テキストを取得 (response.text が存在しない場合のフォールバック)
        md_text = getattr(response, "text", str(response))
        
        # MarkdownをHTMLとプレーンテキストに変換
        html_content = markdown_to_html(md_text)
        plain_text = markdown_to_plaintext(md_text)
        
        print("✅ チャット応答生成完了。")
        return jsonify({"html": html_content, "plain": plain_text})
        
    except Exception as e:
        print(f"❌ Gemini API エラー: {e}")
        return jsonify({"error": f"Gemini API エラー: {e}"}), 500

@app.route("/api/tts", methods=['POST'])
def api_tts():
    """テキストを音声に変換して返す"""
    print("🔊 /api/tts がリクエストされました。")
    d = request.get_json(force=True, silent=True) or {}
    text = d.get("text", "")
    
    if not text:
        return jsonify({"error": "テキストが空です。"}), 400
        
    audio_content = get_ada_voice(text)
    
    if audio_content:
        # 音声データをストリームとして返す
        return send_file(io.BytesIO(audio_content), mimetype="audio/mpeg")
    else:
        return jsonify({"error": "音声生成に失敗しました。"}), 500

@app.route("/api/personalities/add", methods=['POST'])
def add_personality():
    """新しいペルソナを追加する"""
    print("➕ /api/personalities/add がリクエストされました。")
    
    text_content = request.form.get('text_content', '')
    user_defined_name = request.form.get('name', None)

    # ファイルがアップロードされた場合
    if 'file' in request.files:
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "ファイルが選択されていません。"}), 400
            
        filename, file_extension = os.path.splitext(file.filename)
        
        # ファイルを一時的に保存
        # ファイル名に安全でない文字が含まれる可能性があるので、一時ファイル名にはUUIDなどを利用する方がより安全ですが、ここでは簡略化します。
        temp_file_base = "temp_upload_file"
        temp_path = os.path.join(app.root_path, temp_file_base + file_extension)
        
        try:
            file.save(temp_path)
            print(f"一時ファイル '{temp_path}' に保存しました。")
            # ファイルからテキストを抽出
            text_content = extract_text_from_file(temp_path, file_extension)
        except ValueError as e: # extract_text_from_file で発生したエラー
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": f"ファイルの処理中にエラーが発生しました: {e}"}), 500
        finally:
            # 一時ファイルを削除
            if os.path.exists(temp_path):
                os.remove(temp_path)
                print(f"一時ファイル '{temp_path}' を削除しました。")

    # テキストコンテンツが空の場合
    if not text_content:
        return jsonify({"error": "ペルソナ設定テキストが提供されていません。"}), 400

    # ペルソナを保存
    try:
        new_name = save_personality(text_content, user_defined_name)
        print("✅ ペルソナ追加処理完了。")
        return jsonify({"message": f"新しいペルソナ '{new_name}' を追加しました。"})
    except Exception as e:
        print(f"❌ ペルソナ追加処理中にエラーが発生しました: {e}")
        return jsonify({"error": f"ペルソナの保存中にエラーが発生しました: {e}"}), 500

# --------------------------
# アプリケーションの実行
# --------------------------
if __name__ == '__main__':
    # デバッグモードで実行する場合
    # app.run(debug=True, host='0.0.0.0', port=5000)
    
    # 本番環境など、デバッグなしで実行する場合
    # VercelではunicornなどのWSGIサーバーが使われることが多いです。
    # ローカル実行の場合は以下でも可
    app.run(host='0.0.0.0', port=5000)
