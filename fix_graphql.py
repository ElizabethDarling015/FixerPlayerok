import os

# Путь к файлу
file_path = os.path.join('playerokapi', 'graphql_queries.py')

print(f"Читаю файл: {file_path}")
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. ИСПРАВЛЯЕМ СЛОМАННЫЙ БЛОК 'items' ВНУТРИ СЛОВАРЯ
broken_start = "'items': 'a1dcbe"
next_key = "'item': \"\"\""

start_idx = content.find(broken_start)
end_idx = content.find(next_key)

if start_idx != -1 and end_idx != -1:
    correct_items_block = """'items': \"\"\"
query items($filter: ItemFilter, $pagination: Pagination, $sort: Sort, $showForbiddenImage: Boolean) {
items(filter: $filter, pagination: $pagination, sort: $sort) {
edges {
...ItemEdgeFields
__typename
}
pageInfo {
startCursor
endCursor
hasPreviousPage
hasNextPage
__typename
}
totalCount
__typename
}
}
fragment ItemEdgeFields on ItemProfileEdge {
cursor
node {
...ItemEdgeNode
__typename
}
__typename
}
fragment ItemEdgeNode on ItemProfile {
...MyItemEdgeNode
...ForeignItemEdgeNode
__typename
}
fragment MyItemEdgeNode on MyItemProfile {
id
slug
priority
status
name
price
rawPrice
statusExpirationDate
sellerType
attachment(showForbiddenImage: $showForbiddenImage) {
...PartialFile
__typename
}
isAttachmentsForbidden
user {
...UserItemEdgeNode
__typename
}
game {
name
__typename
}
category {
name
__typename
}
approvalDate
createdAt
priorityPosition
viewsCounter
dealsCounter
feeMultiplier
isAutomated
__typename
}
fragment PartialFile on File {
id
url
__typename
}
fragment UserItemEdgeNode on UserFragment {
...UserEdgeNode
__typename
}
fragment UserEdgeNode on UserFragment {
...RegularUserFragment
__typename
}
fragment RegularUserFragment on UserFragment {
id
username
role
avatarURL
isOnline
isBlocked
rating
testimonialCounter
createdAt
supportChatId
systemChatId
__typename
}
fragment ForeignItemEdgeNode on ForeignItemProfile {
id
slug
priority
status
name
price
rawPrice
sellerType
attachment(showForbiddenImage: $showForbiddenImage) {
...PartialFile
__typename
}
isAttachmentsForbidden
user {
...UserItemEdgeNode
__typename
}
game {
name
__typename
}
category {
name
__typename
}
approvalDate
priorityPosition
createdAt
viewsCounter
dealsCounter
feeMultiplier
isAutomated
__typename
}
\"\"\",\n"""
    
    content = content[:start_idx] + correct_items_block + content[end_idx:]
    print("✅ Сломанный блок 'items' успешно заменен на правильный.")
else:
    print("⚠️ Блок 'items' не найден (возможно, уже исправлен).")

# 2. УДАЛЯЕМ МУСОР В САМОМ КОНЦЕ ФАЙЛА
tail_marker = "}\nQUERY_TEXTS['items'] = \"\"\""
if tail_marker in content:
    tail_idx = content.find(tail_marker)
    # Оставляем только закрывающую скобку "}" и удаляем весь хвост
    content = content[:tail_idx + 1] + "\n"
    print("✅ Мусор в конце файла успешно удален.")
else:
    print("⚠️ Мусор в конце файла не найден.")

# Сохраняем исправленный файл
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n🎉 ГОТОВО! Файл сохранен. Теперь запускай бота.")
