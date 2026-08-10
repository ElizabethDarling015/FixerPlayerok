"""Реконструирует GraphQL-документы из JS-бандла playerok.com и вычисляет их sha256
так же, как это делает Apollo persisted-query-link:

  hash = sha256( print( addTypename( gql(source) ) ) )

- gql (graphql-tag) склеивает шаблонный литерал операции с интерполированными
  фрагментами (${var}) и дедуплицирует фрагменты по имени (порядок — первое вхождение).
- Apollo при addTypename=true (по умолчанию) добавляет __typename в конец каждого
  вложенного selection set (кроме корневого selection set операции).
- persisted-query-link берёт sha256 от print(document).
"""
import hashlib
import json
import re
import sys

from graphql import parse, print_ast
from graphql.language import ast as gast
from graphql.language.visitor import visit, Visitor

from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
import argparse
_ap = argparse.ArgumentParser()
_ap.add_argument("--bundle", default=None)
_ap.add_argument("--out", default=str(ROOT / "graphql_collected.json"))
_args = _ap.parse_args()
_bundle_dir = ROOT / "_jsbundle"
if _args.bundle:
    JS = _args.bundle
else:
    _cands = sorted(_bundle_dir.glob("_app-*.js")) if _bundle_dir.is_dir() else []
    if not _cands:
        raise SystemExit("Не найден _jsbundle/_app-*.js — сначала collect_gql.py")
    JS = str(_cands[-1])
print(f"Читаю бандл: {JS}", file=sys.stderr)
src = open(JS, encoding="utf-8", errors="replace").read()

# ---------------------------------------------------------------------------
# 1. Извлекаем все tagged-template литералы gql: VAR=(0,X.Y)`...`  и inline (0,X.Y)`...`
#    templates[var] = сырой текст шаблона с маркерами ${x}
# ---------------------------------------------------------------------------

# gql-тег в бандле — это функция (0,ns.J1) или подобная. Найдём её имя по присутствию
# ключевых слов внутри литерала. Проще: ловим любые (0,IDENT.IDENT)` ... ` и VAR=(0,IDENT.IDENT)`...`

templates = {}          # varname -> raw template (с ${..})
anon_ops = []           # список сырых шаблонов операций без имени переменной

# Найдём позиции всех вхождений `=(0,` + `)`` и `(0,`+`)``.
# Общий приём: сканируем строку, находим бэктик, который сразу после ")" после "(0,IDENT.IDENT)".
tag_re = re.compile(r'(?:(?P<var>[A-Za-z_$][\w$]*)\s*=)?\(0,[A-Za-z_$][\w$]*\.[A-Za-z_$][\w$]*\)`')

def read_template(s, open_bt):
    """Читает содержимое шаблонного литерала начиная с позиции открывающего бэктика."""
    i = open_bt + 1
    buf = []
    while i < len(s):
        c = s[i]
        if c == '\\':
            buf.append(s[i:i+2]); i += 2; continue
        if c == '`':
            return ''.join(buf), i
        buf.append(c); i += 1
    return ''.join(buf), i

for m in tag_re.finditer(src):
    bt = m.end() - 1  # позиция открывающего бэктика
    body, _ = read_template(src, bt)
    if not re.search(r'\b(query|mutation|subscription|fragment)\b', body):
        continue
    var = m.group('var')
    if var:
        # если несколько присваиваний одному имени — берём как есть (последнее перезапишет);
        # имена локальны, коллизии редки, но подстрахуемся суффиксом
        key = var
        if key in templates and templates[key] != body:
            key = f"{var}__{m.start()}"
        templates[key] = body
    else:
        anon_ops.append(body)

print(f"Извлечено tagged-литералов: {len(templates)} именованных, {len(anon_ops)} анонимных", file=sys.stderr)

# ---------------------------------------------------------------------------
# 2. Утилиты
# ---------------------------------------------------------------------------
INTERP_RE = re.compile(r'\$\{([A-Za-z_$][\w$]*)\}')

def interpolations(tmpl):
    return INTERP_RE.findall(tmpl)

def strip_interp(tmpl):
    return INTERP_RE.sub('', tmpl).strip()

def fragment_name(tmpl):
    m = re.search(r'fragment\s+([A-Za-z_][\w]*)\s+on', tmpl)
    return m.group(1) if m else None

def op_header(tmpl):
    m = re.search(r'\b(query|mutation|subscription)\s+([A-Za-z_][\w]*)', tmpl)
    return (m.group(1), m.group(2)) if m else (None, None)

# карта: имя фрагмента -> var (для случаев, если интерполяция ссылается на var, а мы дедупим по имени)
# Здесь интерполяции ссылаются на var напрямую, поэтому строим DFS по var.

def resolve_document(op_tmpl):
    """Возвращает финальный source: операция + уникальные фрагменты (DFS, первое вхождение)."""
    included = []          # порядок var
    included_set = set()
    def dfs(tmpl):
        for x in interpolations(tmpl):
            if x in templates and x not in included_set:
                included_set.add(x)
                included.append(x)
                dfs(templates[x])
    dfs(op_tmpl)
    parts = [strip_interp(op_tmpl)]
    for x in included:
        parts.append(strip_interp(templates[x]))
    return "\n\n".join(parts)

# ---------------------------------------------------------------------------
# 3. addTypename как в Apollo (__typename в конец каждого вложенного selection set,
#    кроме корневого selection set операции)
# ---------------------------------------------------------------------------

def add_typename(document: gast.DocumentNode) -> gast.DocumentNode:
    def has_typename(sel_set):
        for s in sel_set.selections:
            if isinstance(s, gast.FieldNode) and s.name.value == "__typename" and s.alias is None:
                return True
        return False

    def make_typename():
        return gast.FieldNode(name=gast.NameNode(value="__typename"), arguments=(), directives=(), selection_set=None)

    def walk_selection_set(sel_set, is_operation_root):
        if sel_set is None:
            return
        # рекурсивно обрабатываем детей
        for sel in sel_set.selections:
            if isinstance(sel, gast.FieldNode) and sel.selection_set is not None:
                walk_selection_set(sel.selection_set, False)
            elif isinstance(sel, gast.InlineFragmentNode) and sel.selection_set is not None:
                walk_selection_set(sel.selection_set, False)
        # добавляем __typename если не корень операции и ещё нет
        if not is_operation_root and not has_typename(sel_set):
            sel_set.selections = tuple(sel_set.selections) + (make_typename(),)

    for defn in document.definitions:
        if isinstance(defn, gast.OperationDefinitionNode):
            walk_selection_set(defn.selection_set, True)
        elif isinstance(defn, gast.FragmentDefinitionNode):
            walk_selection_set(defn.selection_set, False)
    return document

def compute_hash(source, do_addtypename=True):
    doc = parse(source)
    if do_addtypename:
        doc = add_typename(doc)
    printed = print_ast(doc)
    return hashlib.sha256(printed.encode()).hexdigest(), printed

# ---------------------------------------------------------------------------
# 4. Собираем все операции (именованные шаблоны + анонимные), считаем хэши
# ---------------------------------------------------------------------------
operations = {}   # opname -> {kind, source(resolved), hash_with_typename, hash_no_typename}

def register(tmpl):
    kind, name = op_header(tmpl)
    if not name:
        return
    # только если это операция (начинается с query/mutation/subscription)
    first_kw = re.search(r'\b(query|mutation|subscription|fragment)\b', tmpl)
    if not first_kw or first_kw.group(1) == 'fragment':
        return
    resolved = resolve_document(tmpl)
    try:
        h_typename, printed_t = compute_hash(resolved, True)
    except Exception as e:
        h_typename, printed_t = f"PARSE_ERROR: {e}", None
    try:
        h_plain, _ = compute_hash(resolved, False)
    except Exception:
        h_plain = None
    if name not in operations or (printed_t and len(printed_t) > len(operations[name].get("printed") or "")):
        operations[name] = {
            "operationName": name,
            "kind": kind,
            "sha256Hash": h_typename,
            "sha256Hash_no_typename": h_plain,
            "printed": printed_t,
        }

for tmpl in templates.values():
    register(tmpl)
for tmpl in anon_ops:
    register(tmpl)

print(f"Всего операций: {len(operations)}", file=sys.stderr)

# сохраняем
out = {}
for name, d in operations.items():
    out[name] = {
        "operationName": name,
        "kind": d["kind"],
        "sha256Hash": d["sha256Hash"],
        "query": d["printed"],
    }

with open(_args.out, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(f"Записано {len(out)} операций → {_args.out}", file=sys.stderr)

# ---------------------------------------------------------------------------
# 5. Калибровка: сверяем с известными хэшами библиотеки
# ---------------------------------------------------------------------------
sys.path.insert(0, str(ROOT))
from playerokapi.graphql_queries import PERSISTED_QUERIES as LIB

print("\n=== КАЛИБРОВКА (библиотека vs пересчитанное с сайта) ===", file=sys.stderr)
match = 0
for name, libhash in LIB.items():
    d = operations.get(name)
    if not d:
        print(f"  [НЕТ В БАНДЛЕ] {name}", file=sys.stderr)
        continue
    ok = d["sha256Hash"] == libhash
    okp = d.get("sha256Hash_no_typename") == libhash
    tag = "MATCH" if ok else ("MATCH(no_typename)" if okp else "DIFF")
    if ok:
        match += 1
    print(f"  [{tag}] {name}: lib={libhash[:12]} site={str(d['sha256Hash'])[:12]}", file=sys.stderr)
print(f"\nСовпало точно (с addTypename): {match}/{len(LIB)}", file=sys.stderr)
