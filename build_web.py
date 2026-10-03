"""Embed the authoritative main.py into a browser-playable HTML file."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
source = json.dumps((ROOT / 'main.py').read_text(encoding='utf-8')).replace('</', '<\\/')
template = '''<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#000000">
<title>SWING BLADE｜Pyxel試用版</title>
<style>
html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#000;color:#d5ffff;font-family:system-ui,sans-serif;touch-action:none;overscroll-behavior:none}
#intro{position:fixed;inset:0;z-index:10;display:grid;place-content:center;padding:28px;background:#071019;text-align:center}
h1{font-size:26px;letter-spacing:.12em;color:#55dceb;margin:0 0 8px}p{line-height:1.9;font-size:14px;color:#c2d4df}
button{padding:18px 26px;border:1px solid #55dceb;border-radius:8px;background:#102d39;color:#d5ffff;font-size:17px;font-weight:bold;cursor:pointer}
small{display:block;margin-top:20px;color:#829eae;font-size:12px;line-height:1.7}
#help{position:fixed;bottom:max(2px,env(safe-area-inset-bottom));left:0;right:0;text-align:center;z-index:4;pointer-events:none;font-size:10px;color:#809fa9;background:#0009}
</style></head><body>
<div id="intro"><h1>SWING BLADE</h1><p>移動だけで、巨大な剣を振り回そう。<br>ドラッグして移動 → 切り返して攻撃。<br>30秒生存に挑戦、または敵なし練習。</p>
<button id="boot" disabled>読み込み中…</button><small>START：30秒サバイバル ／ PRACTICE：無傷の練習<br>PC：方向キー・WASD ／ P：一時停止 ／ M：音<br>起動時にインターネット接続が必要です。</small></div>
<div id="help" hidden>ドラッグで移動・切り返しで攻撃｜左上：一時停止　右上：音</div>
<script>
window.swingBlurCount=0;
function suspend(){window.swingBlurCount++;const c=document.querySelector('canvas');if(c){c.dispatchEvent(new MouseEvent('mouseup',{bubbles:true,button:0}));for(const key of ['ArrowUp','ArrowDown','ArrowLeft','ArrowRight','w','a','s','d']){window.dispatchEvent(new KeyboardEvent('keyup',{key,bubbles:true}));}}}
window.addEventListener('blur',suspend);
document.addEventListener('visibilitychange',()=>{if(document.hidden)suspend();});
document.addEventListener('touchcancel',suspend);
document.addEventListener('pointercancel',suspend);
const runtime=document.createElement('script');
runtime.src='https://cdn.jsdelivr.net/gh/kitao/pyxel@2.9.9/wasm/pyxel.js';
const boot=document.getElementById('boot');
runtime.onload=()=>{boot.disabled=false;boot.textContent='起動する';};
runtime.onerror=()=>{boot.textContent='読込失敗：ページを再読み込み';};
document.head.appendChild(runtime);
boot.onclick=()=>{document.getElementById('intro').remove();document.getElementById('help').hidden=false;
launchPyxel({command:'run',script:__GAME_SOURCE__,gamepad:'disabled'}).catch(e=>{document.getElementById('help').textContent='起動に失敗しました。接続を確認し、再読み込みしてください。';console.error(e);});};
</script></body></html>
'''
(ROOT / 'index.html').write_text(template.replace('__GAME_SOURCE__', source), encoding='utf-8')
print('Generated index.html from main.py')
