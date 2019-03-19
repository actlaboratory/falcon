# Falcon
Falcon Pythonで再スタートできればいいな。  
## 準備
シェル:コマンドプロンプト  
python:python 3.7  
python -m pip install wxpython  

## 実行  
python falcon.py  

## exeファイルのビルド  
64-bit バージョンのビルド方法です。32ビットでビルドしたい人は適当に。  
MinGWのCコンパイラをダウンロード ( https://sourceforge.net/projects/mingw-w64/ )  
インストール先を C:\MinGW64 と入力してインストール  
システム環境変数の path に C:\MinGW64\mingw64\bin を追加
gcc --version でちゃんと入ったか確認  
nuitka(exeにするツール)をインストール  
python -m pip install nuitka  
ビルド  
python tools\build.py  
5分ぐらい時間かかるので気長に待って  

## コーディング規則  
docs フォルダの中に書いてあります。  

## 翻訳辞書ファイル(po)のアップデート
python tools\updateTranslation.py  
locale フォルダを勝手に探して、poファイルを配置してくれます。なので、言語を追加したい場合は、locale フォルダに空フォルダを作ってください。前回の翻訳文は残ったままマージされます。文字列が増えたときでも、気にせず updateTranslation してください。  

## 翻訳したら  
python tools\buildTranslation.py  
