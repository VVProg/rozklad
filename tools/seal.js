#!/usr/bin/env node
/* Одноразово шифрує посилання/ID/коди в rozklad.html і кладе пароль у PASSWORD.txt.
   Пароль генерується тут, на цій машині, і нікуди не передається.
   Формат сховища збігається з тим, що читає сторінка: PBKDF2-SHA256 → AES-256-GCM,
   шифротекст із доданим тегом автентифікації (як робить WebCrypto). */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const ROOT = path.join(__dirname, '..');
const SRC = path.join(ROOT, 'rozklad.html');
const PASS_FILE = path.join(ROOT, 'PASSWORD.txt');
const SECRET_FIELDS = ['link', 'classroom', 'meetingId', 'passcode'];
const ITER = 250000;
const DATA_RE = /<script id="app-data" type="application\/json">\s*([\s\S]*?)\s*<\/script>/;

function makePassword() {
  const abc = 'abcdefghjkmnpqrstuvwxyz23456789'; // без 0/o/1/l/i
  const pick = n => Array.from(crypto.randomBytes(n)).map(b => abc[b % abc.length]).join('');
  return ['kn01', pick(4), pick(4), pick(4)].join('-');
}

const src = fs.readFileSync(SRC, 'utf8');
const m = DATA_RE.exec(src);
if (!m) { console.error('не знайдено <script id="app-data"> у rozklad.html'); process.exit(1); }
const data = JSON.parse(m[1].replace(/\\u003c/g, '<'));

if (data.vault) { console.error('розклад уже зашифровано — пароль міняйте на сторінці'); process.exit(1); }

const secrets = {};
let count = 0;
for (const l of data.lessons) {
  const sec = {};
  let any = false;
  for (const f of SECRET_FIELDS) {
    if (l[f]) { sec[f] = l[f]; any = true; }
    l[f] = '';
  }
  l.locked = any;
  if (any) { secrets[l.id] = sec; count++; }
}

const password = makePassword();
const salt = crypto.randomBytes(16);
const iv = crypto.randomBytes(12);
const key = crypto.pbkdf2Sync(password, salt, ITER, 32, 'sha256');
const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
const ct = Buffer.concat([
  cipher.update(JSON.stringify(secrets), 'utf8'),
  cipher.final(),
  cipher.getAuthTag()
]);

data.vault = {
  v: 1, kdf: 'PBKDF2-SHA256', iter: ITER,
  salt: salt.toString('base64'), iv: iv.toString('base64'), ct: ct.toString('base64')
};

const body = JSON.stringify(data, null, 1).replace(/</g, '\\u003c');
fs.writeFileSync(SRC, src.replace(DATA_RE,
  () => '<script id="app-data" type="application/json">\n' + body + '\n</script>'), 'utf8');

fs.writeFileSync(PASS_FILE,
  'Пароль до посилань розкладу КН01-23\n' +
  '(потрібен, щоб побачити Zoom/Classroom і щоб редагувати розклад)\n\n' +
  '    ' + password + '\n\n' +
  'Передайте його групі захищеним каналом. У репозиторії цього файлу немає.\n' +
  'Змінити пароль можна на сторінці: Редагувати → Налаштування → Змінити пароль.\n' +
  'Відновити забутий пароль неможливо — посилання доведеться вводити заново.\n', 'utf8');

console.log('зашифровано занять із посиланнями: ' + count);
console.log('пароль записано у PASSWORD.txt');
