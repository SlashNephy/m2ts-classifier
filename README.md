# m2ts-classifier

🧹 m2ts ファイルを作品ごとにシンボリックリンクを作成し, 整理します

![screenshot1.png](https://i.imgur.com/XSjwXO7.png)

![screenshot2.png](https://i.imgur.com/YgZv3ko.png)

## ロジック

- ファイル名のレーベンシュタイン距離を計算します。距離が小さいほど, タイトルの類似性が高いため同じ作品としてみなします。
- 同じ作品としてみなしたファイル名から共通文字列を算出します。共通文字列が各作品のフォルダになります。
- 実際のファイルを移動させるのではなく, シンボリックリンクを貼るため高速かつ安全に整理を行えます。

## docker-compose

```yml
services:
  classifier:
    container_name: m2ts-classifier
    image: ghcr.io/slashnephy/m2ts-classifier:master
    volumes:
      - /mnt:/mnt:ro
      - /mnt/links:/mnt/links
    environment:
      # 対象とする拡張子, ファイル名の比較をしてるだけなので m2ts じゃなくても使えます
      TARGET_EXTENSION: m2ts
      # リンクの作成場所
      OUTPUT_DIRECTORY: /mnt/links
      # m2ts の保存場所
      MOUNT_POINTS: /mnt

      # 各閾値, 詳しくはソースコード参照
      # ファイル名の編集距離の許容値, これを下回ったものだけが同じ作品とみなされる
      LD_THRESHOLD: 0.5
      # マッチ数の許容値, これを上回った際に作品ごとのフォルダが作られる
      MATCH_THRESHOLD: 4
      # 共通文字列の文字列の長さの許容値, これを上回った際にフォルダが作られる
      SEQUENCE_THRESHOLD: 4

      # https://github.com/SlashNephy/comskip-tvtplay と併用するかどうか
      # .chapter ファイルのシンボリックリンクも作成されるようになる
      SUPPORT_COMSKIP_TVTPLAY: 1
```
