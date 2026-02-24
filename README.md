# Blender 5.x キー表示アドオン雛形

`blender5_min_addon/__init__.py` は Blender 5.x 向けの「押下キー表示」アドオン雛形です。

## 主な機能

- 表示 ON/OFF のトグルオペレータ（`keycon.toggle_display`）
- 対象エリア指定（View3D / Image Editor / Node Editor）
- modifier を含むリアルタイムキー表示（例: `Ctrl+Shift+A`）
- 直近 N 件の履歴表示
- TTL による自動消去 + フェードアウト
- アドオン専用ショートカット登録/解除（`Ctrl+Shift+F8`）
- Preferences で位置・サイズ・表示項目を変更

## インストール

1. `blender5_min_addon` フォルダを ZIP 化する（フォルダごと圧縮）。
2. Blender 5.x を開き、`編集 > プリファレンス > アドオン > インストール` を選択。
3. 作成した ZIP を指定して有効化。

## 使い方

1. 3D View のサイドバー（`N`） > `Tool` > `KeyCon Display` で `Start Key Display` を押す。
2. あるいは `Ctrl+Shift+F8` で ON/OFF。
3. Preferences で以下を調整:
   - 表示位置（X/Y）
   - フォントサイズ
   - 履歴件数
   - TTL
   - modifier / area 表示有無
   - 描画対象エリア
