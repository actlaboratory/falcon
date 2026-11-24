# Falcon
Falcon Pythonで再スタートできればいいな。  
## 準備
シェル:コマンドプロンプト

python:python 3.12 (32bit)  

python -m pip install -r requirements.txt  
python -m pip install --no-deps -r requirements-nodeps.txt  
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

## ライセンス
falcon は Apache License 2.0 で提供されます(LICENSE)。  
同梱している他者の成果物のライセンスは、 public/license.txt と public/license フォルダにあります。  

## 同梱の7-Zip
7zやRARなどの圧縮・解凍には、 bin フォルダの7-Zip(7z.exe / 7z.dll、公式の32bit版を変更せずに同梱)を使います。  
新しいバージョンに更新するときは、7z.exe と 7z.dll を差し替え、 public/license/individual/7-zip.txt のバージョンとソースコードのURL、 7-zip_License.txt、 public/license.txt も合わせて更新してください。  
