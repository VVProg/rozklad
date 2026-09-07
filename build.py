#!/usr/bin/env python3
"""Збирає самодостатній index.html для GitHub Pages з rozklad.html.

Розподіл ролей:
  rozklad.html — джерело коду (CSS + JS). Це фрагмент: його публікує Artifact,
                 який сам додає <!doctype>/<head>/<body>.
  index.html   — те, що віддає GitHub Pages. Повний документ. САМЕ ВІН несе
                 актуальні дані розкладу: сторінка перезаписує його через
                 GitHub API щоразу, коли хтось тисне «Зберегти для всіх».

Тому дані завжди беруться з index.html, якщо він існує, і повертаються назад
у rozklad.html — щоб версія в Artifact не відставала від живої сторінки.
"""
import io, json, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'rozklad.html')
OUT = os.path.join(ROOT, 'index.html')

FONT_HREF = ('https://fonts.googleapis.com/css2?family=Commissioner:wght@300;400;500;600;700'
             '&family=JetBrains+Mono:wght@400;500;700&family=Unbounded:wght@500;700&display=swap')

CSS_RE = re.compile(r'<style id="app-css">(.*?)</style>', re.S)
JS_RE = re.compile(r'<script id="app-js">(.*?)</script>', re.S)
DATA_RE = re.compile(r'<script id="app-data" type="application/json">\s*(.*?)\s*</script>', re.S)


def read(path):
    return io.open(path, encoding='utf-8').read()


def grab(pattern, text, what, path):
    m = pattern.search(text)
    if not m:
        sys.exit('не знайдено %s у %s' % (what, path))
    return m.group(1)


def main():
    src = read(SRC)
    css = grab(CSS_RE, src, '<style id="app-css">', SRC)
    js = grab(JS_RE, src, '<script id="app-js">', SRC)

    # дані — з живої сторінки, якщо вона вже є
    data_src = OUT if os.path.exists(OUT) else SRC
    raw = grab(DATA_RE, read(data_src), '<script id="app-data">', data_src)
    data = json.loads(raw.replace('\\u003c', '<'))

    title = 'Розклад ' + data.get('group', '')
    body = json.dumps(data, ensure_ascii=False, indent=1).replace('<', '\\u003c')

    doc = (
        '<!doctype html>\n<html lang="uk">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<meta name="robots" content="noindex, nofollow">\n'
        '<title>' + title + '</title>\n'
        '<link rel="stylesheet" href="' + FONT_HREF + '">\n'
        '<style id="app-css">' + css + '</style>\n</head>\n<body>\n'
        '<div id="root"></div>\n<div id="layer"></div>\n'
        '<script id="app-data" type="application/json">\n' + body + '\n</script>\n'
        '<script id="app-js">' + js + '</script>\n</body>\n</html>\n'
    )
    io.open(OUT, 'w', encoding='utf-8').write(doc)

    # синхронізуємо дані назад у джерело, щоб Artifact не відставав
    if data_src == OUT:
        io.open(SRC, 'w', encoding='utf-8').write(
            DATA_RE.sub(lambda _: '<script id="app-data" type="application/json">\n' + body + '\n</script>', src, count=1))

    print('index.html: %d занять, %.0f КБ' % (len(data.get('lessons', [])), len(doc.encode('utf-8')) / 1024))


if __name__ == '__main__':
    main()
