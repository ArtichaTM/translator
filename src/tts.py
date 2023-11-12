from pathlib import Path
import os

import torch
from TTS.api import TTS
from pydub import AudioSegment

device = "cuda" if torch.cuda.is_available() else "cpu"
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)


def combine_sentences(sentences):
    # Проверяем, что списка предложений не пусты
    if len(sentences) == 0:
        return
    count = 0
    # Первое предложение
    combined_text = sentences[0]['text']
    combined_start = sentences[0]['start']
    combined_end = sentences[0]['end']
    total_dur = abs(combined_end-combined_start)

    # Объединяем остальные предложения
    for i in range(1, len(sentences)):
        start = sentences[i]['start']
        end = sentences[i]['end']

        # Проверяем интервал между предложениями
        if abs(combined_end-start) < 5:
            combined_text += ' ' + sentences[i]['text']  # Объединяем текст
            combined_end = end  # Обновляем конец объединенного предложения
            total_dur += abs(combined_end-start)
            total_dur += abs(end - start)
        else:
            # Создаем пустой wav файл в промежутке между предложениями
            duration = start - combined_end
            create_silent_wav(duration,count)
            count+=1

            # Создаем wav файла для объединенного предложения
            create_combined_wav(combined_text, total_dur, count)
            count+=1

            # Обновляем начало и конец следующего объединенного предложения
            combined_text = sentences[i]['text']
            combined_start = start
            combined_end = end
            total_dur = 0

    # Создаем wav файла для последнего объединенного предложения
    create_combined_wav(combined_text, total_dur, count)


def create_silent_wav(duration, count, path: Path):
    # Создаем пустой wav файл заданной длительности
    silence = AudioSegment.silent(duration * 1000)
    silence.export(str(path.absolute()), format='wav')


def create_combined_wav(text, total_dur, count):
    # Генерируем и сохраняем wav файл с текстом
    path = "back/" + str(count) + ".wav"
    print(path)
    tts.tts_to_file(text=text, file_path=path, speaker_wav="0.wav", language="en")
    audio = AudioSegment.from_wav(path)
    new_audio = audio[:total_dur * 1000]
    new_audio.export(path, format='wav')


def final():
    combined_sounds = AudioSegment.empty()

    # Укажите путь к папке, содержащей wav файлы
    folder_path = 'back/'

    # Обходите все файлы в папке
    for filename in os.listdir(folder_path):
        if filename.endswith(".wav"):
            # Откройте каждый файл и добавьте его звук в общий объект AudioSegment
            sound = AudioSegment.from_wav(os.path.join(folder_path, filename))
            combined_sounds += sound

    # Сохраните общий звук в новом wav файле
    combined_sounds.export("combined.wav", format="wav")


def tts_line(
        text: str,
        output: Path,
        source_wav_fragment: Path,
        silence_amount: float,
        silence_output: Path
) -> None:
    tts.tts_to_file(
        text=text,
        speaker_wav=str(source_wav_fragment.absolute()),
        file_path=str(output.absolute()),
        language='ru'
    )
    create_silent_wav(silence_amount, None, silence_output)


def main():
    # Пример использования
    print(device)
    tts.tts_to_file(text='Moscow twenty century. How interesting. Pity, video bad quality and can\' distinguish what '
                         'is '
                         'wrote here: taverna, or something other',
                    file_path='output.wav', speaker_wav='3.wav', language='ru')
    # sentences = [
    #     {'text': 'Hello,', 'start': 0, 'end': 2},
    #     {'text': 'my name is Ivan.', 'start': 3, 'end': 5},
    #     {'text': 'Manmay,', 'start': 6, 'end': 8},
    #     {'text': 'how are you?', 'start': 10, 'end': 13}
    # ]
    # combine_sentences(sentences)
    # final()


if __name__ == '__main__':
    main()
