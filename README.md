# Rocal Paper

日本語から英語論文を書き、TeXを学びながら進めるローカル専用デスクトップアプリ。
0.3系はElectronの画面と別プロセスのPython処理サービスで構成します。Chromium・Python・TinyTeX・PDFiumを同梱し、Python・MiKTeX・WebView2の別途導入は不要です。現在は製品化に向けたプレビュー版です。

## 使う

Windows x64で `RocalPaper-Setup-0.3.0.exe` を実行し、保存先を選びます。スタートメニューから起動できます。同じインストーラーの再実行でアプリを更新できます。原稿はアプリ本体と分離して保存し、アンインストールでも自動削除しません。

- 3秒ごとの自動保存、ファイルごとに過去40回の変更前の保存履歴
- 未保存入力を画面とは別のプロセスで復元用下書きに記録、再起動時に復元
- PDF生成・AI待ち中も編集可能。終了操作は処理サービスや画面の応答を待たない
- 日本語→英語の翻訳と表現解説、英文の日本語理解、TeXの説明と例、エラーの説明
- AIなしでも使える見出し・数式・表・図・引用の練習例
- 同梱pdfLaTeX / BibTeX / PDFium、PDF保存、ソースZIP出力
- ローカルAI接続・起動、終了時の所有プロセス回収、診断ログ

標準の保存先は `%LOCALAPPDATA%\RocalPaper`。設定、原稿、復元用下書き、履歴、ログを保存します。履歴は永久バックアップではありません。ソースZIPを定期的に別の保存先へ書き出してください。復元用下書きは最後に編集した1ファイルを対象とし、ファイル切替時は保存を完了してから移動します。

### Dドライブでまとめて使う（ポータブルモード）

EXEと同じ場所、またはその親フォルダーに `portable.json`（内容は `{}` で可）を置くと、原稿・設定・WebViewキャッシュを同じ場所の `data` に保存します。`--data-dir`を指定した場合はそちらを優先します。既存データの自動移動は行いません。

この開発環境の配置は次のとおりです。以前のCドライブ側のコピーはバックアップとして残し、以降はD側を使用します。

| 場所 | 用途 |
| --- | --- |
| `D:\RocalPaper\app\RocalPaper.exe` | 0.3系の起動するアプリ |
| `D:\RocalPaper\source` | Git管理する開発ソース |
| `D:\RocalPaper\data` | 原稿・設定・キャッシュ |
| `D:\RocalPaper\tex` | 既存の同梱TinyTeXを再利用 |
| `D:\RocalPaper\source\build` | 0.3系の再ビルド用中間ファイル |
| `D:\RocalPaper\validation\interspeech2026` | 公式paper kitと検証PDF・ログ |

LLMモデルは既存の `D:\rocalLLM` を参照するため、重複コピーしません。

## ローカルAI

AIなしでも編集・PDF生成は使えます。画面右上の **設定** から次のどちらかを選びます。

1. 起動済みのOpenAI互換ローカルサーバーのURLを保存する（例：`http://127.0.0.1:8080`）。
2. Rocal LLMフォルダーを指定し **ローカルAIを起動**。フォルダーには`model_catalog.json`、`runtime_config.json`、`webui.json`、`models`と設定された`llama-server`が必要です。Rocal Studioの既存実行フォルダーを利用できます。

自分で起動したAIプロセスだけを終了時に停止します。Rocal Studio / QwenPlaygroundとの同時モデルロードを防ぐため、これらのアプリが動作中なら起動を止めます。GGUFや推論エンジンはこの公開ソースに含めません。

外部AIサービスへの接続は受け付けず、ループバックHTTPだけを使います。必要なら起動前の環境変数`ROCAL_PAPER_API_KEY`でローカルサーバーの認証を指定できます。

## ビルド（0.3 Electron版）

Windows x64、Python 3.11、Node.js 24 LTSが必要です。依存バージョンはrequirementsとpackage-lockで固定します。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-desktop.txt
npm ci
.\.venv\Scripts\python.exe build_electron.py
# 既存のTeXを再利用する場合
.\.venv\Scripts\python.exe build_electron.py --tex D:\RocalPaper\tex\TinyTeX
# テスト
.\.venv\Scripts\python.exe -m unittest discover -s paper_studio -v
npm test
```

`dist/electron`にNSISインストーラーと`win-unpacked`が生成されます。ビルド時のみネット接続が必要です。初回は固定版TinyTeXをSHA256確認後に取得します。モデルは別途用意します。

開発起動前に`npm run setup:runtime`でElectronを準備します。開発起動は`ROCAL_PYTHON`にPython実行ファイルを設定し、`npm start -- --tex-root D:\RocalPaper\tex --data-dir D:\RocalPaper\data`。

`build_paper.py`と`paper_studio/desktop.py`は0.2系の比較・移行用です。製品版の起動経路では使用しません。0.3系はElectronが終了・下書きを管理し、処理サービスは親のパイプ切断で終了します。Windows Job ObjectでTeX・モデル等の子プロセスも回収します。PDFiumもさらに別プロセスで実行し、ネイティブ障害を画面から隔離します。

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
- インストーラーとEXEのコード署名、署名検証付き自動更新、クリーンなWindows仮想環境での長時間試験は未完了です。正式な一般配布品質にはまだ達していません。
- 同梱していない特殊なLaTeXパッケージは手動追加が必要です。`tex/TinyTeX/bin/windows/tlmgr.bat install パッケージ名`でアプリ内TeXに追加できます（取得時はネット接続が必要）。
- 共同編集、SyncTeX、Biber/biblatexの自動実行、UIからのZIP取込み・画像アップロード、構文ハイライトは未実装です。保存履歴はアプリ内で利用できます。原稿のGit管理とこのアプリ自体のGit管理は別です。
- 既存の原稿・画像・クラスファイルは、プロジェクトの`source`フォルダーに手動配置して再読込してください。
- AIは段落単位で利用してください。引用・数値・主張は原稿と照合してから反映します。
- 個人用です。TeXのshell escapeは無効ですがOSサンドボックスではないので、信頼する原稿を扱ってください。

## 公開範囲・ライセンス

公開するのはアプリのソース、テスト、ビルドスクリプトです。私的な実験リポジトリの履歴、論文、接続設定、鍵、GGUFは含めません。
Rocal PaperのコードはMIT。第三者のTeX・フォント・ライブラリはそれぞれのライセンスに従います。[THIRD_PARTY.md](THIRD_PARTY.md)を参照してください。第三者バイナリの公開再配布はこのソース公開には含めません。

## 製品化の判断と残課題

[SciPen Studio比較・製品化計画](PRODUCT_PLAN.md)に、採用した設計、未対応機能、出荷前の検証条件を記録しています。
