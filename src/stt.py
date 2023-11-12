"""
https://github.com/GolovninLev/STT
"""

import sys
import subprocess
from io import StringIO
from json import loads
from pathlib import Path
from random import choices
from string import ascii_letters
from typing import Generator
import wave
from vosk import Model, KaldiRecognizer, SetLogLevel


def random_string() -> str:
    return ''.join(choices(ascii_letters, k=20))


def convert_mp4_to_wav(input_file, output_file):
    command = f"bin\\ffmpeg.exe -i {input_file} -ac 1 -acodec pcm_s16le -ar 44100 -vn {output_file}"

    subprocess.run(command.split())




SetLogLevel(0)


model = Model(model_name="vosk-model-small-ru-0.22")


# rec.SetPartialWords(True)


# try:
#     result_default = sys.argv[2]
# except:
#     result_default = Path('./output/result.json')
#     result_default.parent.mkdir(parents=True, exist_ok=True)
#     result_default = str(result_default.absolute())


# command = f"rm {temp_format_file}"
# subprocess.run(command.split())


def process(input: Path, temporary_folder: Path) -> Generator[dict, None, None]:
    if input.name.endswith('.mp4'):
        output = temporary_folder / f"{random_string()}.wav"
        convert_mp4_to_wav((input.absolute()), str(output.absolute()))
        wf = wave.open(str(output.absolute()), "rb")
    else:
        wf = wave.open(str(input), 'rb')
    rec = KaldiRecognizer(model, wf.getframerate())
    rec.SetWords(True)

    if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
        print("Audio file must be WAV format mono PCM.")
        sys.exit(1)

    i = 0
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            i += 1
            yield loads(rec.Result())
        else:
            pass

