# Random-number-LINEbot
最小値と最大値を設定したら乱数を生成してくれるLINEbot「乱数生成くん」を作成。

## 未完成部分  
フラグ管理をグローバル変数で行っており、多人数で同時に扱うことができない。  
解決法: データベースを用いてフラグ管理する。  

### 乱数生成くんのLINEID
`@yij5612k`

### 動作
「乱数」という言葉を含めたメッセージを送ることで乱数生成の準備をはじめます。  
最小値と最大値を答えたら設定完了です。  
その後はメッセージ(スタンプ含む)を送るたび指定された範囲の乱数を生成します。  
「リセット」を含めたメッセージを送ると、今の乱数設定を破棄し最初の状態に戻ります。  
