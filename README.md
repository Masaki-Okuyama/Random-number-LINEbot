# Random-number-LINEbot
最小値と最大値を設定したら乱数を生成してくれるLINEbot「乱数生成くん」を作成。

## 動作
「乱数」という言葉を含めたメッセージを送ることで乱数生成の準備をはじめます。  
最小値と最大値を答えたら設定完了です。  
その後はメッセージ(スタンプ含む)を送るたび指定された範囲の乱数を生成します。  
「リセット」を含めたメッセージを送ると、今の乱数設定を破棄し最初の状態に戻ります。 

## データベース  
ユーザーごとのフラグ管理のためにデータベースを用いています。テーブルの中身は以下の通りです。  
```
FlagTB (
  userID varchar(33),
  minFlag boolean,
  maxFlag boolean,
  randFlag boolean,
  maxNumber int,
  minNumber int,
  stampNum int
);
```

## portpass.py
データベースに繋げる情報はportpass.pyに書き、importしています。

## 乱数生成くんのLINEID
IDは`@yij5612k`  
QRコードは  
![qr](https://github.com/Masaki-Okuyama/Random-number-LINEbot/blob/images/randomku_qr.jpg)
