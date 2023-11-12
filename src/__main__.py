from sys import exit
from argparse import ArgumentParser
from pathlib import Path
from unittest.mock import Mock

from . import FFMpeg, Translator, MediaContainer

get_available_languages_tts = Mock(return_value=['en'])
get_available_languages_stt = Mock(return_value=['ru'])


def main() -> int:
    """Convert in CLI"""
    parser = ArgumentParser(description='Video translation to different langugages')
    parser.add_argument(
        "input",
        type=Path,
        help='Video file that needs to be translated. Allows absolute and relative paths'
    )
    parser.add_argument(
        'output',
        type=Path,
        help='Destination file. Extension matters. Available: .mkv/.mp4'
    )
    parser.add_argument(
        '--subtitles',
        '-s',
        dest='subtitles',
        metavar='language code',
        nargs='*',
        help='Specify code of subtitle to translate'
    )
    parser.add_argument(
        '--audio',
        '-a',
        dest='audio',
        metavar='language code',
        nargs='+',
        required=True,
        help='Specify code of audio to translate'
    )
    parser.add_argument(
        '--available',
        action='store_true',
        help='Print all available languages'
    )
    args = parser.parse_args()
    source: Path = args.input
    target: Path = args.output
    subtitles: set[str] = set(args.subtitles)
    audio: set[str] = set(args.audio)

    codes_stt = set(get_available_languages_stt())
    codes_tts = set(get_available_languages_tts())

    available_subtitles = set(Translator().available_codes())  # Available for translate
    available_subtitles = codes_stt.union(available_subtitles)  # Available for STT and translate
    not_available_subtitles = subtitles.difference(available_subtitles)  # Not available texts
    if not_available_subtitles:
        print(f'Language {next(iter(not_available_subtitles))} are not available for subtitles')
        return 1

    not_available_audio = audio.difference(codes_tts)
    if not_available_subtitles:
        print(f'Language {next(iter(not_available_audio))} are not available for audio')
        return 2

    if args.available:
        print('Available languages:')
        print('\tSource audio: ru')
        print(f"\tSubtitles: {', '.join(available_subtitles)}")
        print(f"\tAudio: {', '.join(codes_tts)}")
        return 3

    if not source.exists():
        print('Source file does not exist')
        return 4

    translator = Translator()

    with FFMpeg(Path('bin/ffmpeg.exe')) as ffmpeg:
        ffmpeg.run(
            source=source,
            target=target,
            audio_codes=audio,
            subtitle_codes=subtitles,
        )
    return 0


if __name__ == '__main__':
    main()
