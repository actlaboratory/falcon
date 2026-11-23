# CLAUDE.md

falcon は、wxPython で作られた、スクリーンリーダー利用者向けのファイラーです。
GUI は ACT Laboratory のテンプレートライブラリ [viewkit](https://github.com/actlaboratory/viewkit) の上に作られています。

## 環境

- Python 3.12 **32bit**（`py -3.12-32`）。仮想環境はリポジトリ直下の `.venv`（git 管理外）
  - 作成: `py -3.12-32 -m venv .venv` → 有効化: `.\.venv\Scripts\Activate.ps1` → `python -m pip install -r requirements.txt` → `python -m pip install --no-deps -r requirements-nodeps.txt`
- 依存パッケージのバージョンは viewkit の指定（wxPython 4.2.2 / Pillow 9.5 / PyInstaller 6.11.0）に合わせる。viewkit 本体は requirements.txt で GitHub のアーカイブ URL（コミット固定）から入れる
- proxyUtil は `dukpy~=0.2.2` を指定しているが、dukpy 0.2 系には 32bit Python 3.12 向けのビルド済みファイルがなく CI でコンパイルにも失敗する。そのため proxyUtil は `requirements-nodeps.txt` に分けて `--no-deps` で入れ、依存パッケージ（dukpy 0.3.1 など）は requirements.txt に書く。proxyUtil は他の管理下なので変更しない
- 実行: `python falcon.py`（`python -m falcon.py` ではない）
- 起動時のドライブ一覧の取得は、接続できないネットワークドライブがあると数十秒かかる。エラーではない

## 作業の基本方針

- **viewkit はテンプレート。viewkit 本体（`.venv` 内や `../viewkit`）は変更しない。** falcon 独自の機能は、viewkit のクラスを継承するなどして falcon 側に実装する
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
| `keymap.py` / `keymapHandlerBase.py` / `defaultKeymap.py` | ショートカットキーの検証と登録。タブの種類によって同じキーを別機能に割り当てられる（例: Delete がファイル一覧ではゴミ箱、ドライブ一覧では取り外し） |
| `menuItemsDic.py` / `menuItemsStore.py` | メニュー項目の表示名と ID。`menuItemsStore` は viewkit の RefStore としても使われる |
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
- スクリーンリーダーでの読み上げなど、実機でしか確認できないことは、未確認であることをユーザーに伝える
