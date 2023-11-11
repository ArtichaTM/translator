## Переводчик
Выполняет перевод с *русского* на другие языки
* Перевод русский -> английский выполняется напрямую
* Остальные языки переводятся через английский
### Установка
* Для Windows можно выполнить файл run.bat
* Для Linux можно выполнить файл run.sh
### Ручная установка
1. Установить библиотеку torch
1. Установить библиотеку argostranslate
1. Выполнить файл check_install.py для установки моделей
### Использование
Всё использование переводчика основывается на вызове методов у класса Translator
```python
from translator import Translator

translator = Translator()

text_translate = translator.translate('Как у тебя дела?', 'en')
text_list = translator.translate_list(['Как у тебя дела?'], 'en')
text_call_translate = translator('Как у тебя дела?', 'en')
text_call_list = translator(['Как у тебя дела?'], 'en')

assert text_translate == text_call_translate == text_list[0] == text_call_list[0]
```
Узнать все доступные коды языков можно командой Translator.available_codes()
```python
from translator import Translator

translator = Translator()
print(translator.available_codes()) # prints ['ar', 'az', ..., 'zh', 'zt']
```
