from typing import Callable, Optional, Union
from pathlib import Path
from abc import ABC
from re import findall, finditer
from itertools import chain
from tempfile import TemporaryDirectory, TemporaryFile
from subprocess import run
from queue import Queue
from threading import Thread
from random import choices
from string import ascii_letters

from .subtitles import subtitles_write, Line
from .translator import Translator


__all__ = ('FFMpeg', 'MediaContainer')


def resolve_path(path: Union[str, Path]) -> Path:
    if isinstance(path, str):
        return Path(path)
    return path


class _DataType(ABC):
    __slots__ = ('index', 'codec', 'language', 'source')

    def __init__(self, index: int, codec: str, language: str, source: Path):
        assert isinstance(index, int)
        assert isinstance(codec, str)
        assert isinstance(language, str)
        assert isinstance(source, Path)
        self.index = index
        self.codec = codec
        self.language = language
        self.source = source


class Video(_DataType):
    __slots__ = ('resolution', 'bitrate', 'fps')

    def __init__(
            self,
            index: int,
            codec: str,
            language: str,
            bitrate: Optional[float],
            source: Union[str, Path],
            resolution: tuple[int, int],
            fps: float
    ):
        super().__init__(index, codec, language, source)
        assert isinstance(bitrate, float) or bitrate is None
        assert isinstance(resolution, tuple)
        assert isinstance(resolution[0], int)
        assert isinstance(resolution[1], int)
        assert isinstance(fps, float)
        self.bitrate = bitrate
        self.resolution = resolution
        self.fps = fps

    def __repr__(self) -> str:
        return f"<Video layer codec={self.codec} fps={self.fps}>"


class Audio(_DataType):
    __slots__ = ('frequency', 'bitrate')

    def __init__(
            self,
            index: int,
            codec: str,
            language: str,
            bitrate: Optional[float],
            source: Union[str, Path],
            frequency: int
    ):
        super().__init__(index, codec, language, source)
        assert isinstance(bitrate, float) or bitrate is None
        assert isinstance(frequency, int)
        self.bitrate = bitrate
        self.frequency = frequency

    def __repr__(self) -> str:
        return f"<Audio layer codec={self.codec} frequency={self.frequency}>"


class Subtitles(_DataType):
    def __repr__(self) -> str:
        return f"<Subtitles layer codec={self.codec} language={self.language}>"


def info_parse(info: str, source: Union[str, Path]) -> tuple[list[Video], list[Audio], list[Subtitles]]:
    output = ([], [], [])
    pattern = r'Stream #0:(\d)(\[[^]]*\])?\(?(\w+)?\)?: (Video|Audio|Subtitle): (\w+) ?[^,\n]*([^\n]*)'
    # : (Video|Audio|Subtitle): (\w+) ?[^,\n]*([^\n]*)
    for line in findall(pattern, info):
        language = line[2]
        codec = line[4]
        index = int(line[0])
        try:
            bitrate = float(next(finditer(r' (\d+) kb/s', line[5])).group(1))
        except StopIteration:
            bitrate = None
        if line[3] == 'Video':
            resolution = next(finditer(r'(\d+)x(\d+)', line[5]))
            resolution = resolution.groups()
            resolution = (int(resolution[0]), int(resolution[1]))
            fps = float(next(finditer(r'(\d+.?\d+) fps', line[5])).group(1))
            output[0].append(Video(
                index=index,
                codec=codec,
                language=language,
                source=source,
                bitrate=bitrate,
                resolution=resolution,
                fps=fps
            ))
        elif line[3] == 'Audio':
            frequency = int(next(finditer(r' (\d+) Hz', line[5])).group(1))
            output[1].append(Audio(
                index=index,
                codec=codec,
                language=language,
                source=source,
                bitrate=bitrate,
                frequency=frequency
            ))
        elif line[3] == 'Subtitle':
            output[2].append(Subtitles(
                index=index,
                codec=line[4],
                language=line[2],
                source=source
            ))
        else:
            print(line)
            raise RuntimeError()
    return output


class MediaContainer:
    __slots__ = ('objects', )

    def __init__(self, *objects: _DataType):
        self.objects = list(objects)

    def __add__(self, other: 'MediaContainer'):
        assert isinstance(other, MediaContainer)
        return type(self)(*self.objects, *other.objects)

    @classmethod
    def from_datatypes(
            cls,
            values: tuple[list[Video], list[Audio], list[Subtitles]]
    ):
        return cls(*chain.from_iterable(values))

    def add(self, data: _DataType) -> None:
        assert isinstance(data, _DataType)
        self.objects.append(data)


class FFMpeg:
    __slots__ = ('ffmpeg', '_tempDirectory', '_tempDirectory_path')

    def __init__(
        self,
        path_ffmpeg: Union[str, Path]
    ):
        self.ffmpeg = path_ffmpeg
        value = self._call_ffmpeg('-version')
        values = value.split('\n')
        try:
            assert 'the FFmpeg developers' in values[0], 'Wrong output from FFMpeg'
            assert values[0].startswith('ffmpeg'), 'Wrong FFMpeg executable'
            assert 'libavformat' in value, "Can't find libavformat"
            assert 'libavcodec' in value, "Can't find libavcodec"
        except AssertionError as e:
            raise ValueError('FFMpeg is not correct') from e

    def __enter__(self):
        self._tempDirectory = TemporaryDirectory()
        self._tempDirectory_path = Path(self._tempDirectory.name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._tempDirectory.cleanup()
        self._tempDirectory = None
        self._tempDirectory_path = None

    def _call_ffmpeg(self, parameters: str) -> str:
        with TemporaryFile(mode='r+') as f:
            run(
                f"{self.ffmpeg} {parameters}",
                stdout=f,
                stderr=f,
                stdin=f,
                shell=True
            )
            f.seek(0)
            return f.read()

    def build_mc(self, path: Union[str, Path], mc: MediaContainer, overwrite_ok: bool = False):
        assert isinstance(mc, MediaContainer)
        assert isinstance(overwrite_ok, bool)
        path = resolve_path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if overwrite_ok:
                path.unlink()
            else:
                raise ValueError('Trying to overwrite file')
        inputs_l = list()
        maps = list()
        no_subtitles = True if path.name.endswith('.mp4') else False
        for object in mc.objects:
            if isinstance(object, Subtitles) and no_subtitles:
                continue
            try:
                input_index = inputs_l.index(object.source)
            except ValueError:
                inputs_l.append(object.source)
                input_index = len(inputs_l)-1
            maps.append(f"-map {input_index}:{object.index}")
        self._call_ffmpeg(
            ' '.join([
                *[f'-i "{i.absolute()}"' for i in inputs_l],
                *maps
            ]) + ' ' +
            ' -c copy -shortest ' +
            '"' + str(path.absolute()) + '"'
        )

    def get_info(self, path: Union[str, Path]) -> tuple[list[Video], list[Audio], list[Subtitles]]:
        path = resolve_path(path)
        if not path.exists():
            raise ValueError('Path is not correct')
        if not path.is_file():
            raise ValueError('Path target is not a files')
        return info_parse(self._call_ffmpeg(f'-i "{path}"'), source=path)

    def analyze_folders(
            self,
            path: Union[str, Path],
            /,
            to_path: Union[str, Path] = None,
            to_stdout: bool = False
    ) -> Optional[dict]:
        path = resolve_path(path)
        output: dict[str, set[Union[float, int, str, tuple[int, int]]]] = dict()

        output['video_fps'] = set()
        output['vido_codec'] = set()
        output['video_resolution'] = set()
        output['video_bitrate'] = set()
        output['video_language'] = set()
        output['audio_codec'] = set()
        output['audio_language'] = set()
        output['audio_bitrate'] = set()
        output['audio_frequency'] = set()

        for i in Path(path).iterdir():
            info = self.get_info(i)
            output['video_fps'].add(info[0][0].fps)
            output['vido_codec'].add(info[0][0].codec)
            output['video_resolution'].add(info[0][0].resolution)
            output['video_bitrate'].add(info[0][0].bitrate)
            output['video_language'].add(info[0][0].language)
            output['audio_codec'].add(info[1][0].codec)
            output['audio_language'].add(info[1][0].language)
            output['audio_bitrate'].add(info[1][0].bitrate)
            output['audio_frequency'].add(info[1][0].frequency)

        values = [
            'Video fps: ' + ', '.join((str(i) for i in output['video_fps'])),
            'Video codec: ' + ', '.join((str(i) for i in output['vido_codec'])),
            'Video resolution: ' + ', '.join((str(i) for i in output['video_resolution'])),
            'Video bitrate: ' + ', '.join((str(i) for i in output['video_bitrate'])),
            'Audio language: ' + ', '.join((str(i) for i in output['audio_language'])),
            'Audio codec: ' + ', '.join((str(i) for i in output['audio_codec'])),
            'Audio bitrate: ' + ', '.join((str(i) for i in output['audio_bitrate'])),
            'Audio frequency: ' + ', '.join((str(i) for i in output['audio_frequency']))
        ]

        if to_path is not None:
            to_path = resolve_path(to_path)
            if not to_path.parent.is_dir():
                to_path.parent.mkdir(parents=True, exist_ok=True)
            to_path.write_text('\n'.join(values), encoding='utf-8')
        elif to_stdout:
            print('\n'.join(values))
        else:
            return output

    def extract_audio(self, video_source: Union[str, Path]) -> Audio:
        """ Extracts aac audio from file to destination
        :param video_source: Path to source video (.mp4 or .mkv)
        :return: Path to extracted audio
        """
        video_source = resolve_path(video_source)
        if not video_source.exists():
            raise ValueError('Path is not correct')
        if not video_source.is_file():
            raise ValueError('Path target is not a files')
        if not (video_source.name.endswith('.mkv') or video_source.name.endswith('.mp4')):
            raise TypeError(f"Undefined type of file {video_source.name}")

        # Get info about video file
        info = self.get_info(video_source)
        assert info[1][0].codec == 'aac', 'Only aac codecs are enabled'

        # Extract aac
        target_aac = self._tempDirectory_path / f"{video_source.name.split('.')[0]}.aac"
        self._call_ffmpeg(f'-i "{video_source}" -vn -acodec copy "{target_aac}"')
        return self.get_info(target_aac)[1][0]

    def aac_to_wav(self, audio_source: Union[str, Path]) -> Audio:
        audio_source = resolve_path(audio_source)
        if not audio_source.exists():
            raise ValueError('Path is not correct')
        if not audio_source.is_file():
            raise ValueError('Path target is not a files')

        # Transcode to wav
        target_wav = self._tempDirectory_path / f"{audio_source.name.split('.')[0]}.wav"
        self._call_ffmpeg(f'-i "{audio_source}" "{target_wav}"')

        return self.get_info(target_wav)[1][0]

    def wav_to_aac(self, audio_source: Union[str, Path]) -> Audio:
        audio_source = resolve_path(audio_source)
        if not audio_source.exists():
            raise ValueError('Path is not correct')
        if not audio_source.is_file():
            raise ValueError('Path target is not a files')

        # Transcode to wav
        target_aac = self._tempDirectory_path / f"{audio_source.name.split('.')[0]}.aac"
        self._call_ffmpeg(f'-i "{audio_source}" "{target_aac}"')

        return self.get_info(target_aac)[1][0]

    def get_wav(
            self,
            video_source: Union[Path, str]
    ) -> Audio:
        video_source = resolve_path(video_source)

        if not video_source.exists():
            raise ValueError('Path is not correct')
        if not video_source.is_file():
            raise ValueError('Path target is not a files')

        aac_file: Audio = self.extract_audio(video_source)
        wav_file: Audio = self.aac_to_wav(aac_file.source)
        return self.get_info(wav_file.source)[1][0]

    def replace_audio_line(
            self,
            video_source: Union[Path, str],
            audio_source: Union[Path, str],
            audio_line: int = 0,
            use_tempdir: bool = True,
    ) -> Path:
        video_source = resolve_path(video_source)
        if not video_source.exists():
            raise ValueError('Path is not correct')
        if not video_source.is_file():
            raise ValueError('Path target is not a files')

        audio_source = resolve_path(audio_source)
        if not audio_source.exists():
            raise ValueError('Path is not correct')
        if not audio_source.is_file():
            raise ValueError('Path target is not a files')

        if use_tempdir:
            new_video_source = self._tempDirectory_path / f"{video_source.name.split('.')[0]}.mp4"
        else:
            new_video_source = video_source.parent / f"{video_source.name.split('.')[0]}_replaced.mp4"

        self._call_ffmpeg(
            f'-i {video_source} '
            f'-i {audio_source} '
            f'-c:v copy '
            f'-map 0:v:0 '
            f'-map 1:a:{audio_line} '
            f'{new_video_source}'
        )
        return new_video_source

    def edit_video(
            self,
            video_source: Union[Path, str],
            changer: Callable[[Path], None],
            replace: bool = False
    ):
        video_source = resolve_path(video_source)
        assert '.' in video_source.name
        wav = self.get_wav(video_source)
        changer(wav.source)
        new_video = self.replace_audio_line(video_source, wav.source, use_tempdir=True)
        if replace:
            video_source.unlink()
            new_video.rename(video_source.absolute())
        else:
            name = video_source.name
            index = name.rfind('.')
            name = name[:index] + '_replaced' + name[index:]
            new_video.rename(video_source.absolute().parent / name)

    def _texts(
            self,
            /,
            russian_texts: Queue[Line],
            translated_texts: Queue[list[Line]],
            audio_codes: set[str],
            subtitle_codes: set[str]
    ) -> None:
        all_codes = audio_codes.union(subtitle_codes)
        translator = Translator()
        if 'ru' in subtitle_codes:
            ru_subs_path = self._tempDirectory_path / f"{''.join(choices(ascii_letters, k=20))}.srt"
            ru_subs_writer = subtitles_write(ru_subs_path)
            next(ru_subs_writer)
            while line := russian_texts.get() is not None:
                ru_subs_writer.send(line)
                translated_lines: list[Line] = []
                for code in all_codes:
                    translated_lines.append(Line(
                        start=line.start,
                        end=line.end,
                        text=translator.translate(line.text, target=code)
                    ))
                translated_texts.put(translated_lines)
                print(f'Completed translating {line}')
        else:
            while line := russian_texts.get() is not None:
                translated_lines: list[Line] = []
                for code in all_codes:
                    translated_lines.append(Line(
                        start=line.start,
                        end=line.end,
                        text=translator.translate(line.text, target=code)
                    ))
                translated_texts.put(translated_lines)

    def _translated_texts(
            self,
            /,
            translated_texts: Queue[list[Line]],
            audio_codes: set[str],
            subtitle_codes: set[str]
    ) -> None:
        while text := translated_texts.get() is not None:
            pass

    def run(
            self,
            source: Path,
            target: Path,
            audio_codes: set[str],
            subtitle_codes: set[str]
    ) -> None:
        assert isinstance(source, Path)
        assert isinstance(target, Path)
        assert isinstance(audio_codes, set)
        assert isinstance(subtitle_codes, set)
        source_info = self.get_info(source)
        source_container = MediaContainer.from_datatypes(source_info)

        russian_texts: Queue[Line] = Queue(maxsize=0)
        translated_texts: Queue[list[Line]] = Queue(maxsize=0)
        text_thread = Thread(
            target=self._texts,
            kwargs={
                'russian_texts': russian_texts,
                'translated_texts': translated_texts,
                'audio_codes': audio_codes,
                'subtitle_codes': subtitle_codes
            },
            name='text analyzer thread'
        )
        text_thread.start()
        translated_text_thread = Thread(
            target=self._translated_texts,
            kwargs={
                'translated_texts': translated_texts,
                'audio_codes': audio_codes,
                'subtitle_codes': subtitle_codes
            },
            name='translated text analyzer thread'
        )
        translated_text_thread.start()

        russian_texts.appe

        translated_audio: list[Audio] = []
        translated_subtitles: list[Video] = []


# TODO: Create many video with different languages
from timeit import default_timer as timer


def main():
    source_mkv = Path(r'C:\Users\Articha\Desktop\EveryThing\Media\Videos\Anime\Fate\ASaber vs Rider.mkv')
    videos_folder = Path(r'C:\Users\Articha\Desktop\Temp\Python\translator\Rutube\videos')
    source_mp4_1 = videos_folder / '8.mp4'
    source_mp4_2 = videos_folder / '12.mp4'
    with FFMpeg(r'bin\ffmpeg.exe') as ffmpeg:
        # ffmpeg.edit_video('ыф.mp4', lambda x: print(x), replace=False)
        new_folder = videos_folder.parent / 'videos2'
        start_time = timer()
        for file in videos_folder.iterdir():
            if not file.name.endswith('.mp4'):
                print('what is it', file)
                continue
            mp4 = ffmpeg.get_info(file)
            aac = ffmpeg.extract_audio(file)
            mc = MediaContainer.from_datatypes(mp4)
            mc.add(aac)
            new_name = new_folder / file.name
            ffmpeg.build_mc(new_name, mc=mc, overwrite_ok=True)
        print(f'Finished in {timer() - start_time}')

        # mp4_1 = ffmpeg.get_info(source_mp4_1)
        # aac_2 = ffmpeg.extract_audio(source_mp4_1)
        # mc = MediaContainer.from_datatypes(mp4_1)
        # mc.add(aac_2)
        # ffmpeg.build_mc('file.mp4', mc=mc, overwrite_ok=True)
        # print()


if __name__ == '__main__':
    main()
