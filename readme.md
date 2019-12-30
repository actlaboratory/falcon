# Falcon
Falcon Pythonで再スタートできればいいな。  
## 準備
シェル:コマンドプロンプト  
python:python 3.7 (3.8にすると動かないので、3.7固定で)  
python -m pip install -r requirements.txt  

## 実行  
python falcon.py  

## falconHelperのビルド  
ネイティブコードで動かしたいものは、C++でギャンギャン書いてあって、 falconHelper.dll になっています。これをビルドするには、 MSVC を入れて、 X86 開発者コマンド・プロンプト上で、以下のコマンドを打ってください。  
cd falconHelper  
make  

## exeファイルのビルド  
python tools\build.py  

## コーディング規則  
docs フォルダの中に書いてあります。  

## 翻訳辞書ファイル(po)のアップデート
python tools\updateTranslation.py  
locale フォルダを勝手に探して、poファイルを配置してくれます。なので、言語を追加したい場合は、locale フォルダに空フォルダを作ってください。前回の翻訳文は残ったままマージされます。文字列が増えたときでも、気にせず updateTranslation してください。  

## 翻訳したら  
python tools\buildTranslation.py  
