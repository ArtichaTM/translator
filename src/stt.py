import sys
import subprocess
import json
import wave

import librosa
import soundfile as sf
from vosk import Model, KaldiRecognizer, SetLogLevel


def convert_mp4_to_wav(input_file, output_file):
    command = f"ffmpeg -i {input_file} -ac 1 -acodec pcm_s16le -ar 44100 -vn {output_file}"
    print(command)
    subprocess.run(command.split())
    print(1)



# temp_format_file = "./app/temp/out.wav"
# 
# convert_mp4_to_wav(sys.argv[1], temp_format_file)

SetLogLevel(0)

x, _ = librosa.load('3.wav', sr=16000)
sf.write('tmp.wav', x, 16000)
wave.open('tmp.wav', 'rb')
wf = wave.open('tmp.wav', "rb")

if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
    print("Audio file must be WAV format mono PCM.")
    sys.exit(1)


model = Model(model_name="vosk-model-small-ru-0.22")


rec = KaldiRecognizer(model, wf.getframerate())
rec.SetWords(True)
# rec.SetPartialWords(True)


print(rec.Result())
print(rec.FinalResult())
print(rec.PartialResult())

# i = 0
# while True:
#     data = wf.readframes(4000)
#     if len(data) == 0:
#         break
#     if rec.AcceptWaveform(data):
#         i += 1
#         with open(result_default.replace('.json', f'{i}.json', 1), 'w') as f:
#             # f.write(rec.Result())
#             new_data(rec.Result())
#     else:
#         pass
#         # f.write(rec.PartialResult())
# 
# 
# command = f"rm {temp_format_file}"
# subprocess.run(command.split())
