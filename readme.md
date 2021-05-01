# Falcon
Falcon Pythonで再スタートできればいいな。  
## 準備
シェル:コマンドプロンプト

python:python 3.8 (3.7以下では動作しません)  

python -m pip install -r requirements.txt  
または make setup  


.exeではなく.pyから実行する場合、一部機能を正しく実行するには.pyを *可変個引数を受け入れる形で* python.exeに関連付けしている必要がある。通常の関連付けではうまく動作しないので注意。  
具体的には、.pyに対する関連付けを以下のようにする。pythonがD:\python\python.exeにある場合、  
"D:\python\python.exe" "%1" %*


## 実行  
python falcon.py  
または make run  
または make  


## falconHelperのビルド  
ネイティブコードで動かしたいものは、C++でギャンギャン書いてあって、 falconHelper.dll になっています。これをビルドするには、 MSVC を入れて、 X86 開発者コマンド・プロンプト上で、以下のコマンドを打ってください。  
cd falconHelper  
nmake  

## exeファイルのビルド  
python tools\build.py  
または make build  

## コードの自動整形
make fmt  

## コーディング規則  
docs フォルダの中に書いてあります。  

## 翻訳辞書ファイル(po)のアップデート
python tools\updateTranslation.py  
locale フォルダを勝手に探して、poファイルを配置してくれます。なので、言語を追加したい場合は、locale フォルダに空フォルダを作ってください。前回の翻訳文は残ったままマージされます。文字列が増えたときでも、気にせず updateTranslation してください。  

## 翻訳したら  
python tools\buildTranslation.py
新規言語の場合は、constants.SUPPORTING_LANGUAGEに言語コードを追加
