# flake8: noqa: E501
"""Self-decrypting HTML backup for seeqret.

Produces a single, dependency-free .html file containing the vault's
secrets encrypted under a password. Opening the file in any modern
browser prompts for the password and decrypts everything client-side
using only the Web Crypto API -- no network requests, no external
scripts, no bundled libraries (CSP-safe and offline).

Crypto: PBKDF2-SHA256 (600k iterations) derives an AES-256-GCM key from
the password + a random 16-byte salt; the payload is encrypted under a
random 12-byte IV. AES-GCM authenticates the ciphertext, so a wrong
password (or tampering) fails cleanly. The envelope format and the
embedded viewer are byte-for-byte the same scheme jseeqret uses, so a
backup produced by either tool decrypts in the same HTML page
(cross-compatible).
"""
import base64
import json
import os
from datetime import datetime, timezone

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

PBKDF2_ITERATIONS = 600000
SALT_BYTES = 16
IV_BYTES = 12


def _derive_key(password, salt):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return kdf.derive(password.encode('utf-8'))


def encrypt_payload(plaintext, password):
    """Encrypt a plaintext string under a password and return the base64
    envelope embedded in the HTML backup.
    """
    salt = os.urandom(SALT_BYTES)
    iv = os.urandom(IV_BYTES)
    key = _derive_key(password, salt)
    # AESGCM.encrypt appends the 16-byte tag to the ciphertext, exactly
    # like the browser's crypto.subtle, so the envelope is decryptable by
    # the embedded Web Crypto viewer.
    ct = AESGCM(key).encrypt(iv, plaintext.encode('utf-8'), None)
    return {
        'v': 1,
        'kdf': 'PBKDF2-SHA256',
        'iter': PBKDF2_ITERATIONS,
        'cipher': 'AES-256-GCM',
        'salt': base64.b64encode(salt).decode('ascii'),
        'iv': base64.b64encode(iv).decode('ascii'),
        'ct': base64.b64encode(ct).decode('ascii'),
    }


def default_backup_filename():
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    return 'seeqret-backup-{}.html'.format(stamp)


def to_self_decrypting_html(plaintext, password, created=None, title=None):
    """Build a self-contained, password-protected HTML backup."""
    if not password:
        raise ValueError(
            'a password is required to create an encrypted backup')

    created = created or datetime.now(timezone.utc).strftime(
        '%Y-%m-%dT%H:%M:%SZ')
    title = title or 'seeqret encrypted backup'

    envelope = encrypt_payload(plaintext, password)
    envelope['created'] = created
    # Escape `<` so the JSON can never break out of the <script> block.
    envelope_json = json.dumps(envelope).replace('<', '\\u003c')

    return (_HTML_TEMPLATE
            .replace('__ENVELOPE_JSON__', envelope_json)
            .replace('__TITLE__', title)
            .replace('__CREATED__', created))


_HTML_TEMPLATE = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root { color-scheme: light dark }
* { box-sizing: border-box }
body {
    margin: 0; padding: 2rem;
    font: 15px/1.5 system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
    background: #0f1117; color: #e6e6e6;
}
.card {
    max-width: 480px; margin: 4rem auto; padding: 2rem;
    background: #1a1d27; border-radius: 12px;
    box-shadow: 0 8px 30px rgba(0,0,0,.4);
}
h1 { font-size: 1.25rem; margin: 0 0 .25rem }
.muted { color: #8b90a0; font-size: .85rem }
input[type=password], input[type=search] {
    width: 100%; padding: .6rem .7rem; margin-top: 1rem;
    border: 1px solid #333845; border-radius: 8px;
    background: #0f1117; color: #e6e6e6; font-size: 1rem;
}
button {
    margin-top: 1rem; padding: .6rem 1rem; border: 0; border-radius: 8px;
    background: #3b82f6; color: #fff; font-size: 1rem; cursor: pointer;
}
button:hover { background: #2f6fe0 }
button.mini {
    margin: 0 0 0 .4rem; padding: .15rem .5rem;
    font-size: .75rem; background: #333845;
}
.err { color: #f87171; margin-top: .75rem; min-height: 1.2em; font-size: .85rem }
#app { display: none; max-width: 1100px; margin: 0 auto }
.toolbar { display: flex; gap: 1rem; align-items: center; flex-wrap: wrap }
.toolbar input { margin-top: 0; flex: 1; min-width: 200px }
.toolbar button { margin-top: 0 }
table { width: 100%; border-collapse: collapse; margin-top: 1.5rem }
th, td {
    text-align: left; padding: .5rem .6rem;
    border-bottom: 1px solid #262a36; vertical-align: top;
    word-break: break-word;
}
th { color: #8b90a0; font-weight: 600; font-size: .8rem; text-transform: uppercase }
.masked { letter-spacing: 2px; color: #8b90a0 }
.shown { font-family: ui-monospace, Menlo, Consolas, monospace }
pre { white-space: pre-wrap; word-break: break-word; background: #0f1117;
    padding: 1rem; border-radius: 8px; overflow: auto }
</style>
</head>
<body>
<script id="vault" type="application/json">__ENVELOPE_JSON__</script>

<div id="gate" class="card">
    <h1>__TITLE__</h1>
    <p class="muted">Encrypted backup &middot; created __CREATED__</p>
    <p class="muted">AES-256-GCM &middot; PBKDF2-SHA256. Everything is
    decrypted locally in your browser; nothing is sent anywhere.</p>
    <form id="unlock">
        <input id="pw" type="password" placeholder="Backup password"
            autocomplete="off" autofocus>
        <div id="err" class="err"></div>
        <button type="submit">Unlock</button>
    </form>
</div>

<div id="app">
    <div class="toolbar">
        <strong id="summary"></strong>
        <input id="search" type="search" placeholder="Filter secrets...">
        <button id="download">Download JSON</button>
    </div>
    <table>
        <thead>
            <tr><th>App</th><th>Env</th><th>Key</th><th>Type</th><th>Value</th></tr>
        </thead>
        <tbody id="rows"></tbody>
    </table>
</div>

<script>
(function () {
    'use strict'

    var env = JSON.parse(document.getElementById('vault').textContent)
    var gate = document.getElementById('gate')
    var appView = document.getElementById('app')
    var form = document.getElementById('unlock')
    var pw = document.getElementById('pw')
    var err = document.getElementById('err')
    var summary = document.getElementById('summary')
    var search = document.getElementById('search')
    var tbody = document.getElementById('rows')
    var plaintext = null

    if (!window.crypto || !window.crypto.subtle) {
        err.textContent = 'This browser cannot decrypt the backup: the Web '
            + 'Crypto API is unavailable. Open the file in a recent version '
            + 'of Chrome, Edge, or Firefox.'
        pw.disabled = true
        return
    }

    function b64_to_bytes(b64) {
        var bin = atob(b64)
        var out = new Uint8Array(bin.length)
        for (var i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i)
        return out
    }

    async function decrypt(password) {
        var base_key = await crypto.subtle.importKey(
            'raw', new TextEncoder().encode(password),
            'PBKDF2', false, ['deriveKey'])
        var key = await crypto.subtle.deriveKey(
            { name: 'PBKDF2', salt: b64_to_bytes(env.salt),
              iterations: env.iter, hash: 'SHA-256' },
            base_key, { name: 'AES-GCM', length: 256 }, false, ['decrypt'])
        var buf = await crypto.subtle.decrypt(
            { name: 'AES-GCM', iv: b64_to_bytes(env.iv) },
            key, b64_to_bytes(env.ct))
        return new TextDecoder().decode(buf)
    }

    function cell(text) {
        var td = document.createElement('td')
        td.textContent = text == null ? '' : String(text)
        return td
    }

    function value_cell(value) {
        var td = document.createElement('td')
        var span = document.createElement('span')
        span.className = 'masked'
        span.textContent = '••••••••'
        var shown = false
        var reveal = document.createElement('button')
        reveal.className = 'mini'
        reveal.textContent = 'reveal'
        reveal.onclick = function () {
            shown = !shown
            span.textContent = shown ? String(value)
                : '••••••••'
            span.className = shown ? 'shown' : 'masked'
            reveal.textContent = shown ? 'hide' : 'reveal'
        }
        var copy = document.createElement('button')
        copy.className = 'mini'
        copy.textContent = 'copy'
        copy.onclick = function () {
            navigator.clipboard.writeText(String(value)).then(function () {
                copy.textContent = 'copied'
                setTimeout(function () { copy.textContent = 'copy' }, 1200)
            })
        }
        td.appendChild(span)
        td.appendChild(reveal)
        td.appendChild(copy)
        return td
    }

    function render(text) {
        plaintext = text
        var data
        try { data = JSON.parse(text) } catch (e) { data = null }

        if (!data || !Array.isArray(data.secrets)) {
            var pre = document.createElement('pre')
            pre.textContent = text
            tbody.parentNode.replaceWith(pre)
            summary.textContent = 'Decrypted (raw)'
            return
        }

        summary.textContent = data.secrets.length + ' secrets'
            + (data.from ? ' from ' + data.from : '')
        data.secrets.forEach(function (s) {
            var tr = document.createElement('tr')
            tr.appendChild(cell(s.app))
            tr.appendChild(cell(s.env))
            tr.appendChild(cell(s.key))
            tr.appendChild(cell(s.type || 'str'))
            tr.appendChild(value_cell(s.value))
            tbody.appendChild(tr)
        })
    }

    function do_search() {
        var q = search.value.toLowerCase()
        var rows = tbody.querySelectorAll('tr')
        rows.forEach(function (tr) {
            var hit = tr.textContent.toLowerCase().indexOf(q) !== -1
            tr.style.display = hit ? '' : 'none'
        })
    }

    function download() {
        var blob = new Blob([plaintext], { type: 'application/json' })
        var url = URL.createObjectURL(blob)
        var a = document.createElement('a')
        a.href = url
        a.download = 'seeqret-backup.json'
        document.body.appendChild(a)
        a.click()
        a.remove()
        URL.revokeObjectURL(url)
    }

    form.addEventListener('submit', async function (e) {
        e.preventDefault()
        err.textContent = ''
        pw.disabled = true
        try {
            var text = await decrypt(pw.value)
            gate.style.display = 'none'
            appView.style.display = 'block'
            render(text)
            search.addEventListener('input', do_search)
            document.getElementById('download').addEventListener('click', download)
        } catch (ex) {
            err.textContent = 'Wrong password, or the file is corrupted.'
            pw.disabled = false
            pw.focus()
            pw.select()
        }
    })
})()
</script>
</body>
</html>
'''
