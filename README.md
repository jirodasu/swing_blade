# SWING BLADE — Pyxel試用版 v0.1

移動による慣性で巨大な剣を振り回す、縦画面のアクション試作。
元作品とこの試作の制作者：jirodasu。

## 遊び方

- **START / 30 SEC**：HPがなくなる前に30秒生き残ればクリア。
- **PRACTICE / NO DAMAGE**：接触ダメージなし。固定された標的で切り返しを練習。
- **スマホ**：画面を押した位置を基準にドラッグして移動。指を離すと減速。
- **PC**：方向キー・WASD、またはマウスでドラッグ。
- **攻撃**：移動方向を切り返して剣を振る。攻撃ボタンなし。止まった剣は攻撃しない。
- **一時停止**：左上の II または P。再開も同じ操作。
- **音**：右上の SND/OFF または M。
- **タイトルへ戻る**：PCでは Esc。リザルトでは TITLE。

HPは5。ダメージ後は短時間無敵。敵は通常型と2回命中が必要な丈夫な型。
これは操作感を評価するための独立した試用版で、元作品の完全再現ではない。

## Windowsで起動

GitHubの Code → Download ZIP から取得して展開。
PowerShellで展開先を開き、以下を実行：

```powershell
py -m pip install -r requirements.txt
py main.py
```

## ブラウザで起動

`index.html` はゲームコードを埋め込んだHTML。Webランタイムの読み込みにはインターネット接続が必要。
「起動する」→ランタイム読込後に表示される画面をタップ→STARTまたはPRACTICE。

ローカルで配信する場合：

```powershell
py -m http.server 8000
```

ブラウザで `http://localhost:8000` を開く。

GitHub Pagesを利用する場合は、リポジトリの Settings → Pages で
「Deploy from a branch」「main」「/ (root)」を選択。
リポジトリの非公開設定とアカウントの契約によりPagesの利用条件が異なる。
この実装では公開設定の変更・Pagesの有効化は行っていない。

## 開発・確認

```powershell
py -m unittest discover -s tests -v
py build_web.py
```

`main.py` が正本。変更後は `build_web.py` で `index.html` を更新する。
Pyxelはネイティブ版・Web版とも2.9.9に固定。

調整の入口：`LENGTH`（剣長）、移動速度1.55、慣性係数.24、復元係数.013、
減衰.97、回転速度上限.30、命中速度閾値1.8、`ROUND_FRAMES`（生存時間）。
命中判定は刃の移動を補間し、速い回転で敵をすり抜けにくくしている。
ブラウザで画面離脱・タッチキャンセルが発生すると一時停止し、手動で再開する。
スマホSafari実機での操作感・音の確認は別途必要。
