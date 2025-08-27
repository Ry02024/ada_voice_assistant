document.addEventListener('DOMContentLoaded', () => {
    const themeToggleBtn = document.getElementById('theme-toggle-btn');
    const sunIcon = document.getElementById('theme-toggle-sun');
    const moonIcon = document.getElementById('theme-toggle-moon');
    const chatBox = document.getElementById('chat-box');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const personaSelect = document.getElementById('persona-select');
    const voiceSelect = document.getElementById('voice-select');
    const ttsToggle = document.getElementById('tts-toggle');
    const addPersonaModal = document.getElementById('add-persona-modal');
    const closeModalBtn = addPersonaModal ? addPersonaModal.querySelector('.close-modal-btn') : null;
    const addPersonaForm = document.getElementById('add-persona-form');
    const editorViewBtn = document.getElementById('editor-view-btn');
    const chatViewBtn = document.getElementById('chat-view-btn');
    const chatView = document.getElementById('chat-view');
    const editorViewContent = document.getElementById('editor-view-content');
    let currentAudio = null;

    // テーマ切り替え処理
    const applyTheme = (isDark) => {
        if (isDark) {
            document.documentElement.classList.add('dark');
            sunIcon.classList.add('hidden');
            moonIcon.classList.remove('hidden');
        } else {
            document.documentElement.classList.remove('dark');
            sunIcon.classList.remove('hidden');
            moonIcon.classList.add('hidden');
        }
    };
    const toggleTheme = () => {
        const isDark = document.documentElement.classList.toggle('dark');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
        applyTheme(isDark);
    };

    // UI初期化処理
    async function initializeUI() {
        await loadPersonalities(); // ペルソナリストをロード
        loadVoices(); // ボイスリストをロード
        showChatView(); // チャットビューを初期表示
        addMessage('bot', 'こんにちは！何かお話しましょう。'); //初期メッセージの表示
    }

    // ペルソナリストの読み込み
    async function loadPersonalities() {
        try {
            const response = await fetch('/api/personalities');
            const data = await response.json();
            personaSelect.innerHTML = ''; // 既存のオプションをクリア

            // デフォルトアシスタントを追加
            const defaultOption = document.createElement('option');
            defaultOption.value = 'Default Assistant';
            defaultOption.textContent = 'Default Assistant';
            personaSelect.appendChild(defaultOption);

            // 取得したペルソナを追加
            data.personalities.forEach(p => {
                const option = document.createElement('option');
                option.value = p;
                option.textContent = p;
                personaSelect.appendChild(option);
            });

            // 区切り線と追加オプションを追加
            const separator = document.createElement('option');
            separator.disabled = true;
            separator.textContent = '──────────';
            personaSelect.appendChild(separator);

            const addOption = document.createElement('option');
            addOption.value = 'add_new_persona';
            addOption.textContent = '＋ New Persona';
            personaSelect.appendChild(addOption);
            
            // 初期表示で "Default Assistant" が選択されるように設定
            personaSelect.value = 'Default Assistant';
        } catch (error) {
            console.error('Error loading personalities:', error);
            // エラーが発生した場合でも、デフォルトアシスタントは表示させる
            personaSelect.innerHTML = '<option value="Default Assistant">Default Assistant</option>';
            personaSelect.value = 'Default Assistant';
        }
    }

    // ボイスリストの読み込み (現在はダミーデータ)
    function loadVoices() {
        voiceSelect.innerHTML = '';
        // 将来的にAPIからボイスを取得するように変更できます。
        const availableVoices = [ { id: 'ada_voice', name: 'Ada (Default)' } ];
        availableVoices.forEach(v => {
            const option = document.createElement('option');
            option.value = v.id;
            option.textContent = v.name;
            voiceSelect.appendChild(option);
        });
        const separator = document.createElement('option');
        separator.disabled = true;
        separator.textContent = '──────────';
        voiceSelect.appendChild(separator);
        const addOption = document.createElement('option');
        addOption.value = 'add_new_voice';
        addOption.textContent = '＋ New Voice';
        voiceSelect.appendChild(addOption);
    }

    // メッセージ送信処理
    async function sendMessage() {
        const prompt = userInput.value.trim();
        if (!prompt) return;

        const selectedPersonality = personaSelect.value;
        addMessage('user', prompt); // ユーザーメッセージを追加
        userInput.value = ''; // 入力フィールドをクリア
        toggleSendButton(false); // 送信ボタンを無効化

        // ローディング表示用メッセージを追加
        const loadingBubble = addMessage('bot', null, true);

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt, personality: selectedPersonality })
            });

            if (!response.ok) throw new Error(`Server error: ${response.statusText}`);
            const data = await response.json();

            // ローディング表示を応答に置き換え
            if (loadingBubble) {
                loadingBubble.innerHTML = data.html;
            } else {
                addMessage('bot', data.html); // メッセージを追加
            }

            // TTSが有効なら音声再生
            if (ttsToggle.checked && data.plain) {
                await playAudio(data.plain);
            }
        } catch (error) {
            console.error('Error:', error);
            const errorText = `<p class="text-red-400">申し訳ありません、エラーが発生しました。</p>`;
            if (loadingBubble) {
                loadingBubble.innerHTML = errorText;
            } else {
                addMessage('bot', errorText);
            }
        } finally {
            toggleSendButton(true); // 送信ボタンを有効化
            chatBox.scrollTop = chatBox.scrollHeight; // チャットボックスをスクロール
        }
    }

    // メッセージをチャットボックスに追加する関数
    function addMessage(sender, content, isLoading = false) {
        const messageContainer = document.createElement('div');
        messageContainer.className = `flex w-full ${sender === 'user' ? 'justify-end' : 'justify-start'}`;

        let messageBubble;
        if (sender === 'bot') {
            // ボットメッセージの場合
            const avatar = document.createElement('div');
            avatar.className = 'avatar';
            avatar.textContent = 'A';
            messageBubble = document.createElement('div');
            messageBubble.className = 'message-bubble bot-message';
            if (isLoading) {
                messageBubble.innerHTML = `<div class="loading-dots"><span></span><span></span><span></span></div>`;
            } else {
                messageBubble.innerHTML = content;
            }
            messageContainer.appendChild(avatar);
            messageContainer.appendChild(messageBubble);
        } else {
            // ユーザーメッセージの場合
            messageBubble = document.createElement('div');
            messageBubble.className = 'message-bubble user-message';
            messageBubble.textContent = content;
            messageContainer.appendChild(messageBubble);
        }
        chatBox.appendChild(messageContainer);
        chatBox.scrollTop = chatBox.scrollHeight; // 自動スクロール
        return messageBubble; // ローディング状態の更新のために返す
    }

    // 送信ボタンの有効/無効を切り替える
    function toggleSendButton(enabled) {
        sendBtn.disabled = !enabled;
    }

    // 音声再生処理
    async function playAudio(text) {
        if (currentAudio) {
            currentAudio.pause(); // 再生中の音声を停止
        }
        const selectedVoiceId = voiceSelect.value;
        try {
            const audioResponse = await fetch('/api/tts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text, voice_id: selectedVoiceId })
            });
            if (audioResponse.ok) {
                const audioBlob = await audioResponse.blob();
                const audioUrl = URL.createObjectURL(audioBlob);
                currentAudio = new Audio(audioUrl);
                currentAudio.play();
            } else {
                console.error('Error generating audio:', await audioResponse.text());
            }
        } catch (error) {
            console.error('Error playing audio:', error);
        }
    }

    // ペルソナ追加モーダルのフォーム送信処理
    async function handleAddPersona(e) {
        e.preventDefault();
        const formData = new FormData(addPersonaForm);
        try {
            const response = await fetch('/api/personalities/add', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            alert(data.message || data.error); // 結果をアラート表示
            if (response.ok) {
                addPersonaModal.classList.add('hidden'); // モーダルを閉じる
                addPersonaForm.reset(); // フォームをリセット
                await loadPersonalities(); // ペルソナリストを再読み込み
            }
        } catch (error) {
            alert('ペルソナの追加中にエラーが発生しました。');
        }
    }

    // --- イベントリスナーの設定 ---
    themeToggleBtn.addEventListener('click', toggleTheme); // テーマ切り替えボタン
    sendBtn.addEventListener('click', sendMessage); // 送信ボタン
    userInput.addEventListener('keypress', (e) => { // Enterキーで送信
        if (e.key === 'Enter' && !sendBtn.disabled) {
            sendMessage();
        }
    });
    if (closeModalBtn) closeModalBtn.addEventListener('click', () => addPersonaModal.classList.add('hidden'));
    if (addPersonaModal) {
        addPersonaModal.addEventListener('click', (e) => { // モーダル外クリックで閉じる
            if (e.target === addPersonaModal) {
                addPersonaModal.classList.add('hidden');
            }
        });
    }
    if (addPersonaForm) addPersonaForm.addEventListener('submit', handleAddPersona); // ペルソナ追加フォーム

    // --- モーダル内要素の参照とイベント ---
    const personaFileInputModal = document.getElementById('persona-file-input-modal');
    const selectedFileNameModal = document.getElementById('selected-file-name-modal');
    const modalCancelBtn = document.getElementById('modal-cancel-btn');
    const modalSaveBtn = document.getElementById('modal-save-btn');
    const modalAiSummary = document.getElementById('modal-ai-summary');
    const modalSyncSummary = document.getElementById('modal-sync-summary');
    const modalRefreshSummary = document.getElementById('modal-refresh-summary');

    if (personaFileInputModal && selectedFileNameModal) {
        personaFileInputModal.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                selectedFileNameModal.textContent = e.target.files[0].name;
            } else {
                selectedFileNameModal.textContent = '';
            }
        });
    }

    if (modalCancelBtn) modalCancelBtn.addEventListener('click', (e) => { e.preventDefault(); addPersonaModal.classList.add('hidden'); });
    // modalSaveBtn はフォームのsubmitで処理されるため個別のclickは不要
    if (modalSyncSummary) modalSyncSummary.addEventListener('click', () => {
        // サマリーを中央のテキストエリアに同期
        const textArea = document.getElementById('persona-text-modal');
        if (textArea && modalAiSummary) textArea.value = modalAiSummary.textContent || '';
    });
    if (modalRefreshSummary) modalRefreshSummary.addEventListener('click', async () => {
        // 将来的にAI要約を取得する処理をここに実装
        if (modalAiSummary) modalAiSummary.textContent = 'Refreshing summary...';
        // 簡易的に現在のテキストからプレースホルダ要約を作る
        const textArea = document.getElementById('persona-text-modal');
        if (modalAiSummary) modalAiSummary.textContent = (textArea && textArea.value) ? textArea.value.slice(0, 400) : 'No persona text provided.';
    });

    // ペルソナ選択の変更イベントハンドラ (修正)
    personaSelect.addEventListener('change', async (e) => {
        const selectedValue = e.target.value;
        if (selectedValue === 'add_new_persona') {
            // "+ New Persona" が選択されたら、エディタビューを新規作成モードで開く
            await showEditPersonaView('add_new_persona');
            e.target.value = 'Default Assistant'; // 選択をリセット
        } else if (selectedValue === 'Default Assistant') {
            // Default Assistant が選択された場合は、チャットビューを表示
            showChatView();
        } else {
            // 選択されたペルソナ名で編集画面を表示
            await showEditPersonaView(selectedValue);
        }
    });

    // チャットビューとエディタビューの切り替え関数
    function showChatView() {
        chatView.classList.remove('hidden');
        editorViewContent.classList.add('hidden');
        // Chatボタンをアクティブに
        chatViewBtn.classList.add('bg-purple-600', 'text-white'); 
        chatViewBtn.classList.remove('bg-gray-200', 'dark:bg-gray-700', 'dark:hover:bg-gray-600', 'text-gray-800', 'dark:text-white');
        // Editorボタンを非アクティブに
        editorViewBtn.classList.add('bg-gray-200', 'dark:bg-gray-700', 'dark:hover:bg-gray-600', 'text-gray-800', 'dark:text-white'); 
        editorViewBtn.classList.remove('bg-purple-600', 'text-white');
    }

    function showEditPersonaView(personaName = null) { // personaName は編集対象のペルソナ名
        return new Promise(async (resolve) => {
            chatView.classList.add('hidden');
            editorViewContent.classList.remove('hidden');
            // Editorボタンをアクティブに
            editorViewBtn.classList.add('bg-purple-600', 'text-white'); 
            editorViewBtn.classList.remove('bg-gray-200', 'dark:bg-gray-700', 'dark:hover:bg-gray-600', 'text-gray-800', 'dark:text-white');
            // Chatボタンを非アクティブに
            chatViewBtn.classList.add('bg-gray-200', 'dark:bg-gray-700', 'dark:hover:bg-gray-600', 'text-gray-800', 'dark:text-white'); 
            chatViewBtn.classList.remove('bg-purple-600', 'text-white');

            // 新規作成モードの処理
            if (personaName === 'add_new_persona') {
                // フィールドをクリアして新規作成モードにする
                document.getElementById('editor-persona-name').value = '';
                document.getElementById('editor-persona-text').value = '';
                document.getElementById('selected-file-name').textContent = '';
                // タイトルを変更
                const titleEl = editorViewContent.querySelector('.editor-title');
                if (titleEl) titleEl.textContent = 'Add New Persona';
            } else if (personaName && personaName !== 'Default Assistant') {
                // 既存のペルソナを編集する場合
                try {
                    const response = await fetch(`/api/personalities/${personaName}`); // 新しいAPIエンドポイント
                    if (response.ok) {
                        const data = await response.json();
                        // 編集画面のフィールドにペルソナデータを表示
                        document.getElementById('editor-persona-name').value = personaName; // personaName をそのまま設定
                        document.getElementById('editor-persona-text').value = data.system_instruction;
                        document.getElementById('selected-file-name').textContent = ''; // ファイル名はクリア
                    } else if (!personaName) {
                        // personaName が null の場合 (例: Editorボタンから直接遷移した場合)
                        alert("編集するペルソナを選択してください。");
                        showChatView(); // チャットビューに戻る
                    }
                    // personaName が 'Default Assistant' の場合、編集画面は空の状態で表示する（あるいはチャットビューに戻る）
                    else if (personaName === 'Default Assistant') {
                        document.getElementById('editor-persona-name').value = ''; // 名前は空にする
                        document.getElementById('editor-persona-text').value = ''; // テキストも空にする
                        document.getElementById('selected-file-name').textContent = ''; // ファイル名もクリア
                        // 必要であれば、'Default Assistant' の編集は無効にするなどの処理を追加
                    }
                } catch (error) {
                    console.error("ペルソナ編集画面でのエラー:", error);
                    alert("ペルソナデータの取得中にエラーが発生しました。");
                    showChatView(); // チャットビューに戻る
                }
            } else if (!personaName) {
                 // personaName が null の場合 (例: Editorボタンから直接遷移した場合)
                 alert("編集するペルソナを選択してください。");
                 showChatView(); // チャットビューに戻る
            } else if (personaName === 'Default Assistant') {
                // Default Assistant が選択された場合
                document.getElementById('editor-persona-name').value = ''; // 名前は空にする
                document.getElementById('editor-persona-text').value = ''; // テキストも空にする
                document.getElementById('selected-file-name').textContent = ''; // ファイル名もクリア
            }
            resolve();
        });
    }
    
    // エディタビューとチャットビューの切り替えボタンのイベントリスナー
    editorViewBtn.addEventListener('click', () => {
        // 編集画面を開く前に、現在選択されているペルソナ名を取得して渡す
        const selectedPersona = personaSelect.value;
        if (selectedPersona && selectedPersona !== 'Default Assistant') {
            showEditPersonaView(selectedPersona);
        } else if (selectedPersona === 'Default Assistant') {
            // Default Assistant が選択されている場合は、編集画面を空で表示
            showEditPersonaView('Default Assistant');
        } else {
            // ペルソナが選択されていない場合
            alert("編集するペルソナを選択してください。");
            showChatView(); // チャットビューに戻る
        }
    });
    chatViewBtn.addEventListener('click', showChatView);

    // 初期テーマ設定
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    applyTheme(savedTheme === 'dark' || (!savedTheme && prefersDark));

    // UIの初期化
    initializeUI();

    // --- ペルソナ編集画面の保存処理 ---
    // 編集画面の保存ボタンにイベントリスナーを追加
    const editorSaveBtn = document.getElementById('save-persona-btn'); // IDを正確に
    const editorCancelBtn = document.getElementById('cancel-persona-btn'); // IDを正確に

    if (editorSaveBtn) {
        editorSaveBtn.addEventListener('click', async () => {
            const personaNameInput = document.getElementById('editor-persona-name'); // IDを正確に
            const personaTextarea = document.getElementById('editor-persona-text'); // IDを正確に

            const personaName = personaNameInput.value.trim();
            const personaText = personaTextarea.value.trim();

            if (!personaName || !personaText) {
                alert('ペルソナ名と設定テキストは必須です。');
                return;
            }

            try {
                // 更新用のAPIエンドポイントにPOSTリクエスト
                const response = await fetch('/api/personalities/update', { // APIエンドポイントを確認
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: personaName, text_content: personaText })
                });
                const data = await response.json();
                alert(data.message || data.error);
                if (response.ok) {
                    await loadPersonalities(); // ペルソナリストを更新
                    showChatView(); // チャットビューに戻る
                }
            } catch (error) {
                console.error('ペルソナ保存時のエラー:', error);
                alert('ペルソナの保存中にエラーが発生しました。');
            }
        });
    }

    // キャンセルボタンの処理
    if (editorCancelBtn) {
        editorCancelBtn.addEventListener('click', () => {
            showChatView(); // チャットビューに戻る
        });
    }

    // 閉じるボタンのイベントリスナー（編集画面の「×」ボタン）
    const editorCloseBtn = editorViewContent.querySelector('.editor-close-btn'); // HTMLで付与したクラスを利用
    if (editorCloseBtn) {
        editorCloseBtn.addEventListener('click', () => {
            showChatView(); // チャットビューに戻る
        });
    }

    // ファイル選択時の表示更新 (editor-persona-file のchangeイベント)
    const editorPersonaFile = document.getElementById('editor-persona-file');
    const selectedFileNameDisplay = document.getElementById('selected-file-name');
    if (editorPersonaFile && selectedFileNameDisplay) {
        editorPersonaFile.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                selectedFileNameDisplay.textContent = e.target.files[0].name;
            } else {
                selectedFileNameDisplay.textContent = '';
            }
        });
    }
});