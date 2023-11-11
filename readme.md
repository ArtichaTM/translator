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
## Перекодировщик
Извлекает из разных форматов видео аудиофайлы. Позволяет конвертировать аудиофайлы в wav, c wav в aac
### Установка
* Для использования основного класса *FFMpeg* требуется указать путь к ffmpeg. В линуксе можно просто его установить командой `apt install ffmpeg` и указывать путь `'ffmpeg'`
### Использование
```python
from transcoder import FFMpeg

# Указываем путь к ffmpeg
path =  'ffmpeg'            # Linux
path = r'bin/ffmpeg.exe'    # Windows

# Создаём класс и выполняем в контекстном менеджере. Это нужно для того,
# чтобы в конце удалялись все временные файлы
with FFMpeg(path) as ffmpeg:
    # Выполняет следующие операции:
    # 1. Извлекает из файла аудиодорожку
    # 2. Конвертирует её в wav
    # 3. Подаёт путь к wav файлу к функции во втором аргументе
    # 4. Создаёт контейнер с изначальным видео и новой дорожкой
    # 5. При параметре replace:
    # 5.1. repalce=True: заменяет изначальный файл
    # 5.2. replace=False: создаёт файл с суффиксом "_replaced"
    ffmpeg.edit_video('ыф.mp4', lambda x: print(x), replace=False)
```
## Субтитры
Создаёт субтитры на основе начала и конца текста и самого текста
### Установка
Не требуется, все зависимости из std python
### Ограничения
* Невозможно изменять уже занесённые строчки
* Невозможно изменять порядок после занесения строчек (для этого можно создать список и потом всё вместе вставить)
### Использование
```python
from subtitles import subtitles_write, Line

# Создаём генератор, записывающий в файл
writer = subtitles_write('subls.srt')

# Выполняем до первого запросы строки
next(writer)

# Подаём класс Line
writer.send(Line(20, 30, 'Hello'))

# Подаём список классов Line
writer.send([
    Line(33, 40, 'Q'),
    Line(44, 50, 'QQ')
])
```


Сгенерированный файл:
```
1
00:00:20,000 --> 00:00:30,000
Hello

2
00:00:33,000 --> 00:00:40,000
Q

3
00:00:44,000 --> 00:00:50,000
QQ
```
