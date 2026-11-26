# CLAUDE.md

falcon は、wxPython で作られた、スクリーンリーダー利用者向けのファイラーです。
GUI は ACT Laboratory のテンプレートライブラリ [viewkit](https://github.com/actlaboratory/viewkit) の上に作られています。

## 環境

- Python 3.12 **32bit**（`py -3.12-32`）。仮想環境はリポジトリ直下の `.venv`（git 管理外）
  - 作成: `py -3.12-32 -m venv .venv` → 有効化: `.\.venv\Scripts\Activate.ps1` → `python -m pip install -r requirements.txt`
- 依存パッケージのバージョンは viewkit の指定（wxPython 4.2.2 / Pillow 9.5 / PyInstaller 6.11.0）に合わせる。viewkit 本体は requirements.txt で GitHub のアーカイブ URL（コミット固定）から入れる
- 32bit Python 3.12 向けのビルド済みファイルがないパッケージは、CI でのコンパイルに失敗する。新しい版で 32bit 向けが出なくなることがあるので、依存パッケージの版を上げるときは 32bit 向けのビルド済みファイルがあるかを確かめる（例: proxyUtil が使う dukpy は 0.3.1 に固定）。proxyUtil は他の管理下なので変更しない
- 実行: `python falcon.py`（`python -m falcon.py` ではない）
- ドライブ一覧では、ネットワークドライブの容量を一覧の作成時には調べず、ドライブごとの専用スレッドで後から取得する（`tabs/driveList.py`）。接続できないドライブは数十秒後に種類が「ネットワーク（未接続）」になる。エラーではない
- 移動先の確認とファイル一覧・共有フォルダの一覧の取得は、`background_wait.run()` により別スレッドで行う。0.3秒で終わらないときは中止できる「読み込み中」ウィンドウ（`views/waiting.py`）を出す。接続できないときは数十秒後に `errorCodes.NETWORK_UNAVAILABLE` になる

## 作業の基本方針

- **viewkit はテンプレート。viewkit 本体（`.venv` 内や `../viewkit`）は変更しない。** falcon 独自の機能は、viewkit のクラスを継承するなどして falcon 側に実装する
- **名前に `base` を含むファイル（`tabs/base.py`、`lists/base.py`、`tabs/searchResultTabBase.py` など）は変更しない。** 他の actlab のプロジェクトと共通にしているため。修正が必要な場合は、呼び出し側や別のモジュールで対応する（例: プレビュー・先頭/末尾の読み上げは `content_reader.py`）
- viewkit の不具合は falcon 側で回避し、回避箇所にコメントを書き、ユーザーに報告する
- 新しく書く・書き直すコードは viewkit のコーディング規約（`../viewkit/docs/coding_conventions.md`、PEP8 準拠）に従う
  - 関数・変数・新規モジュール名は `snake_case`、クラスは `PascalCase`、定数は `SCREAMING_SNAKE_CASE`、非公開は `_` 始まり
  - 文字列はダブルクォート、関数・クラスには docstring、コメントは日本語
  - viewkit のメソッドをオーバーライドするときは viewkit 側の名前（`getSetting`、`showSubWindow` など camelCase）をそのまま使う
  - 既存の古いコード（tabs/, lists/ など）は、触る範囲だけ新しい書き方にそろえる。無関係な箇所の一括リネームはしない
- 翻訳対象の文字列は `_()` で囲む。`_` は gettext なので、使わない戻り値の受け取りには `dummy` を使う（`edit, dummy = creator.inputbox(...)`）
- 既存の機能を壊さないこと。挙動が変わる場合は、報告時に明記する
- コミットメッセージは日本語。1行目に要約、空行の後に箇条書きで変更内容
- ブランチ名は作業内容を表す snake_case（例: `replace_new_kit`）。master への push など外部に出る操作は確認してから行う

## 構成

| 場所 | 役割 |
|---|---|
| `falcon.py` | 起動。旧設定の移行 → `viewkit.ApplicationContext` 生成 → `app.FalconApp` 実行 |
| `app.py` | `FalconApp(viewkit.App)`。音声・効果音・プロキシ・アップデート・ユーザコマンドなど falcon 固有の初期化。`globalVars.app` で参照される |
| `falcon_settings.py` | falcon 固有の設定。viewkit の設定ファイル `settings.json` の `custom.falcon` に「セクション→キー→値」で保存。旧 `settings.ini`/`keymap.ini` からの自動移行もここ |
| `views/main.py` | `MainWindow(viewkit.MainWindow)`。タブ管理、機能（Feature）とメニューの定義、falcon 独自のメニュー・ショートカット管理（`FalconMenu`） |
| `views/*.py`（ダイアログ） | すべて `viewkit.SubWindow` の派生。一覧編集系は `views/key_value_setting.py`（viewkit の `KeyValueSettingWindow` を継承）を使う |
| `views/ViewCreator.py` | viewkit の `ViewCreator` にフォントと `FalconVirtualListCtrl` を適用したもの。タブ内の部品生成で使う |
| `views/menuBlocker.py` | タブの種類・選択項目に応じて無効にするメニューの定義 |
| `keymap.py` / `defaultKeymap.py` | ショートカットキーの検証（`KeyFilter`）と登録（`Keymap`）。キー名とキーコードの対応は viewkit の表を使う。タブの種類によって同じキーを別機能に割り当てられる（例: Delete がファイル一覧ではゴミ箱、ドライブ一覧では取り外し。`permit_conflict` で判定） |
| `menuItemsDic.py` / `menuItemsStore.py` | メニュー項目の表示名と ID。`menuItemsStore` は viewkit の RefStore としても使われる |
| `archiver.py` / `bin/` | 圧縮と解凍。ZIP・TAR系以外は同梱の7-Zip（`bin/7z.exe`）だけを使う（インストール版は使わない） |
| `network_resource.py` | ネットワーク上のコンピューターの列挙（シェルの「ネットワーク」フォルダを使う。WNetOpenEnum は SMB1 依存で使えない）、共有フォルダの一覧、認証 |
| `network_drive.py` / `network_place.py` | ネットワークドライブの割り当て・切断と、ネットワークの場所（`Network Shortcuts` フォルダ内の desktop.ini＋target.lnk）の追加・削除・一覧。ネットワークの場所はドライブ一覧に `browsableObjects.NetworkPlace` として表示する。FTP・SFTP の場所は Windows の形式で保存できないので、設定の `remote_places`（名前→URL）に保存する |
| `remote_storage.py` / `remote_connect.py` / `remote_transfer.py` | FTP・FTPS（Explicit）・SFTP の閲覧、転送（ダウンロード・アップロード。同じ名前があるときは別名・スキップ・上書き・新しい場合だけ上書き・続きから）、フォルダ・空ファイルの作成、名前の変更、同じサーバー内の移動、削除、パーミッションの変更。転送と削除は `remote_transfer` のジョブを `operation_manager` の `DownloadOperation` / `UploadOperation` / `RemoteDeleteOperation` で実行する。サーバー上の項目のコピー・切り取りは Windows のクリップボードに入れられないので `remote_clipboard.py` で覚え（クリップボードには URL の文字列を入れ、更新番号が変わったら無効）、ファイル一覧での貼り付けでダウンロードする。開いたファイルの編集は `remote_edit.py` で追跡し、falcon のウィンドウに戻ったときにアップロードするかを尋ねる。場所は `sftp://user@host:port/path` の URL で表し、`tabs/remote_list.py`（`RemoteListTab`）と `lists/remote.py` で表示する。`remote_storage` は別スレッド用で画面に触らず、認証・SFTP のホスト鍵・FTPS の証明書の確認は例外で知らせ、`remote_connect.run()` がメインスレッドで画面を出してやり直す。パスワードはメモリと（指定時のみ）Windows の資格情報マネージャーに保存し、設定ファイルや URL には入れない。確認したホスト鍵は `known_hosts`（設定ファイルと同じ場所）に保存する。SFTP は paramiko を使う（読み込みが遅いので使うときだけ import） |
| `operation_manager.py` / `views/operation_progress.py` | コピー・移動・圧縮・解凍・削除を別スレッドで順番に実行し（場所が重ならない削除は待たずに始める）、進行状況を表示する。画面やフォーカスを勝手に切り替えず、終了・確認待ちは読み上げで知らせる。プログレスバーは、メインウィンドウか進行状況のウィンドウのどちらか一方だけに表示する（スクリーンリーダーの報告が重ならないように） |
| `fileOperator/elevation.py` / `fileop.py` | アクセス拒否になったファイル操作を、falcon 自身を `--fileop` 付きで管理者権限で起動してやり直す（別の exe は使わない）。受け渡しは名前付きパイプと JSON のみで、pickle と一時ファイルは使わない。管理者権限の側はファイル（ログ・設定）に書き込まない。割り当てたネットワークドライブは見えないので UNC パスにして渡す |
| `background_wait.py` | 時間のかかる処理を別スレッドで実行し、ウィンドウを固めずに待つ。渡す関数の中で画面の部品や表示中の一覧を変更しないこと |
| `tabs/`, `lists/`, `browsableObjects.py` | タブ（ファイル一覧・ドライブ一覧・検索結果など）とその中身 |

### 設定の読み書き

- falcon 固有: `globalVars.app.settings.get_int(section, key, default, min, max)` / `get_bool` / `get_str` / `get` / `set` / `get_section` / `replace_section`。保存は `globalVars.app.save_settings()`
- viewkit 管理（ウィンドウ位置、`view.font`、`view.is_dark`、`view.is_word_wrap`、`shortcuts`）: `globalVars.app.ctx.settings.getSetting("view.is_dark")` / `changeSetting(...)`
- キー名は小文字で扱う（ini 由来）。お気に入り・ここで開くのセクションは名前がキーなので例外

### ダイアログの作り方・開き方

```python
class FooWindow(viewkit.SubWindow):
    def __init__(self, parent, ctx, title, parameters):
        super().__init__(parent, ctx, title, parameters)
        creator = self.creator.makeChild(wx.VERTICAL, 20)
        self.edit, dummy = creator.inputbox(_("名前"), default_value=parameters)
        footer = self.creator.makeChild(wx.HORIZONTAL, 20, style=wx.ALIGN_RIGHT)
        footer.okbutton(_("ＯＫ"), self._on_ok)   # 検証して問題なければ event.Skip()
        footer.cancelbutton(_("キャンセル"))

    def result(self):
        return self.edit.GetLineText(0)

# 呼び出し側
result = globalVars.app.main_window.showSubWindow(FooWindow, _("タイトル"), parameters)
if result.code == wx.ID_CANCEL:
    return
value = result.user_object
```

- パラメータが複数ある場合は `XxxParameters` クラスを作って渡す
- 入力値の検証はウィンドウの OK ボタンのハンドラで行い、ウィンドウを閉じずにエラーを出す

### メニュー項目（機能）を追加するとき

1. `menuItemsDic.py` に識別子（大文字、例 `TOOL_FOO`）と表示名を追加
2. `views/main.py` の `define_menu()` にアクセスキー付きで追加（`_menu_item("TOOL_FOO", "F")`）
3. `views/main.py` の `_get_feature_handlers()` に処理を追加（アクティブなタブのメソッドを呼ぶだけなら `tab("MethodName")`）
4. 既定のショートカットキーがあれば `defaultKeymap.py` に追加（既存ユーザーの `settings.json` には自動では入らない）
5. タブの種類や選択項目によって使えない場合は `views/menuBlocker.py` に追加

## viewkit の既知の不具合（falcon 側で回避済み）

- `ViewModeCalculator` が `MODE_WRAPPING` を参照できず、折り返し有効時に例外 → `views/ViewCreator.py` で補っている
- `ApplicationContext` が `wx.App` より前にフォントを作り、wx のアサーション（wxWidgets Debug Alert）になる → `falcon.py` で先に `wx.DisableAsserts()`
- ショートカットキーの検証が `alt+f4`・`shift+f10` を禁止し、`ctrl+r/F2` のような複数キー指定も捨てる → キーは falcon の `keymap` で管理し、`MainWindow._applyCustomShortcuts` は無効化
- ウィンドウ位置が負（最大化時など）だと設定の保存で例外 → `MainWindow._windowMove` で負の座標は保存しない
- `MainWindow.showSubWindow` は開発時（exe でない時）に例外を捕まえて「リロードエラー」画面を出す。そのときの戻り値は `ModalResult` ではない

## 確認方法

- 変更後は、少なくとも全モジュールの import と `python falcon.py` での起動を確認する。`errorLog.txt` が作られていないこと、`falcon.log` に ERROR がないことを見る
- 画面を変更した場合は、そのウィンドウを生成・レイアウト・`result()` 取得・破棄できることを確認する。自動で閉じるには `wx.CallLater(500, window.EndModal, wx.ID_OK)` などを使う
- テスト用に起動した falcon はタイムアウトなどで必ず終了させる。wx のアサーションダイアログを出したままにしない
- スクリーンリーダーでの読み上げなど、実機でしか確認できないことは、未確認であることをユーザーに伝える。ただし、プルリクエストの説明にはスクリーンリーダーの動作が未確認であることを書かない
