# Rocal Paper

英語論文の執筆・推敲のための、ローカル専用デスクトップLaTeXエディター。
Python・TinyTeX（TeX Live）・PDFiumをアプリにまとめるので、利用者がPythonやMiKTeXを別途インストールする必要はありません。

## 使う

Windows x64で、ビルドしたフォルダーの **RocalPaper.exe** を開きます。
`_internal` と `tex` も含め、フォルダー全体を保持してください。EXEだけのコピーでは動作しません。
Windows 10/11のMicrosoft Edge WebView2 Runtimeを使用します。未導入の環境では[Microsoft公式配布](https://developer.microsoft.com/microsoft-edge/webview2/)から導入してください。

- 複数プロジェクト・複数ファイルのLaTeX編集
- 同梱pdfLaTeX / BibTeXでPDFを生成し、同梱PDFiumで表示
- PDF保存、ソースZIP出力
- ローカルLLMによる英文推敲・学術英訳・構成レビュー・LaTeXエラー説明
- 生成した提案を確認し、選択した原稿に反映
- 終了時の未保存確認、二重起動防止、ローカルAIの起動・停止

原稿の保存先は `%LOCALAPPDATA%\RocalPaper\projects`。接続設定は同じ親フォルダーの`settings.json`です。
アプリを更新しても保存先は変わりません。保存はCtrl+S、またはファイル切替・PDF生成・ZIP出力時。定期自動保存はありません。

### Dドライブでまとめて使う（ポータブルモード）

EXEと同じ場所に `portable.json`（内容は `{}` で可）を置くと、原稿・設定・WebViewキャッシュを同じ場所の `data` に保存します。`--data-dir`を指定した場合はそちらを優先します。既存データの自動移動は行いません。

この開発環境の配置は次のとおりです。以前のCドライブ側のコピーはバックアップとして残し、以降はD側を使用します。

| 場所 | 用途 |
| --- | --- |
| `D:\RocalPaper\RocalPaper.exe` | 起動するアプリ |
| `D:\RocalPaper\source` | Git管理する開発ソース |
| `D:\RocalPaper\data` | 原稿・設定・キャッシュ |
| `D:\RocalPaper\tex` | 既存の同梱TinyTeXを再利用 |
| `D:\RocalPaper\build` | 再ビルド用の中間ファイル |
| `D:\RocalPaper\validation\interspeech2026` | 公式paper kitと検証PDF・ログ |

LLMモデルは既存の `D:\rocalLLM` を参照するため、重複コピーしません。

## ローカルAI

AIなしでも編集・PDF生成は使えます。画面右上の **設定** から次のどちらかを選びます。

1. 起動済みのOpenAI互換ローカルサーバーのURLを保存する（例：`http://127.0.0.1:8080`）。
2. Rocal LLMフォルダーを指定し **ローカルAIを起動**。フォルダーには`model_catalog.json`、`runtime_config.json`、`webui.json`、`models`と設定された`llama-server`が必要です。Rocal Studioの既存実行フォルダーを利用できます。

自分で起動したAIプロセスだけを終了時に停止します。Rocal Studio / QwenPlaygroundとの同時モデルロードを防ぐため、これらのアプリが動作中なら起動を止めます。GGUFや推論エンジンはこの公開ソースに含めません。

外部AIサービスへの接続は受け付けず、ループバックHTTPだけを使います。必要なら起動前の環境変数`ROCAL_PAPER_API_KEY`でローカルサーバーの認証を指定できます。

## ビルド

ビルド時のみPython 3.11 x64とインターネット接続が必要です。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-desktop.txt
.\.venv\Scripts\python.exe build_paper.py
```

`dist/RocalPaper/RocalPaper.exe` が生成されます。TinyTeX v2026.11の公式アーカイブ（約247MB）を初回取得しSHA256検証後に展開します。数千のパッケージを含むTeX Live完全版ではありませんが、標準的な論文に使うパッケージとフォントを含みます。実行時のパッケージ自動ダウンロードはしません。

ビルドの最後に、生成EXE自身でPATHからPython・MiKTeX・外部PDFビューアーを除いた状態の自己テストを実行します。同梱TeX・BibTeX・PDFiumで引用付き論文を処理できなければビルドは失敗します。レポートはアプリフォルダーの`self-test.json`です。

```powershell
# 保存先やビルドキャッシュを変更
.\.venv\Scripts\python.exe build_paper.py --output D:\RocalPaper --cache D:\build-cache\RocalPaper
# 既存TeXを保持してアプリだけ更新（再ダウンロード・再コピーなし）
.\.venv\Scripts\python.exe build_paper.py --output D:\RocalPaper --cache D:\RocalPaper\build --reuse-tex
# ソースのデスクトップ起動（同梱TeX準備後）
.\.venv\Scripts\python.exe -m paper_studio.desktop --tex-root .\dist\RocalPaper
# テスト
.\.venv\Scripts\python.exe -m unittest discover -s paper_studio -v
```

## Interspeech 2026で試す

公式サイトが案内するpaper kitを取得し、review版とcamera-ready版をそれぞれプロジェクトとして作成して検証できます。既存プロジェクトの上書きはしません。

```powershell
.\.venv\Scripts\python.exe validate_interspeech.py --app-root D:\RocalPaper
```

アプリを起動し、`Interspeech 2026 — review validation` または `camera-ready validation` を選択します。メインファイルは`template.tex`です。両方とも6ページ、追加パッケージ不要で生成を確認しました。[検証結果](VALIDATION.md)

原稿・画像・文献ファイル・日付・TeX実行ファイルやパッケージ索引が同じ場合、保存済みのPDFとページ画像を再利用します。APIの`force: true`で再コンパイルできます。変更を検出した場合は新しい一時ディレクトリーで作り直します。

Windowsでは推論プロセスをJob Objectで所有し、アプリの異常終了時も子のモデルプロセスを終了させます。通常の終了だけに依存しません。

## 制限

- 現在の配布対象はWindows x64。macOS / Linuxのアプリパッケージは未実装です。
- WebView2はOS側の前提です。Python、MiKTeX、外部PDFレンダラーは不要です。
- 同梱していない特殊なLaTeXパッケージは手動追加が必要です。`tex/TinyTeX/bin/windows/tlmgr.bat install パッケージ名`でアプリ内TeXに追加できます（取得時はネット接続が必要）。
- 共同編集、SyncTeX、Biber/biblatexの自動実行、UIからのZIP取込み・画像アップロード、構文ハイライト、原稿の版管理は未実装です。原稿のGit管理とこのアプリ自体のGit管理は別です。
- 既存の原稿・画像・クラスファイルは、プロジェクトの`source`フォルダーに手動配置して再読込してください。
- AIは段落単位で利用してください。引用・数値・主張は原稿と照合してから反映します。
- 個人用です。TeXのshell escapeは無効ですがOSサンドボックスではないので、信頼する原稿を扱ってください。

## 公開範囲・ライセンス

公開するのはアプリのソース、テスト、ビルドスクリプトです。私的な実験リポジトリの履歴、論文、接続設定、鍵、GGUFは含めません。
Rocal PaperのコードはMIT。第三者のTeX・フォント・ライブラリはそれぞれのライセンスに従います。[THIRD_PARTY.md](THIRD_PARTY.md)を参照してください。第三者バイナリの公開再配布はこのソース公開には含めません。
