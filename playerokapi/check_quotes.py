# check_quotes.py
with open('playerokapi/graphql_queries.py', 'r', encoding='utf-8') as f:
    text = f.read()
    
count = text.count('"""')
print(f"Количество тройных кавычек в файле: {count}")

if count % 2 != 0:
    print("❌ ОШИБКА: Количество нечетное! Где-то в файле не хватает закрывающих или открывающих кавычек \"\"\"")
else:
    print("✅ Количество кавычек четное. Ошибка может быть в пробелах между ними или в структуре словаря.")