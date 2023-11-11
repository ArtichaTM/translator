from typing import Callable, Optional, Union
from pathlib import Path
from abc import ABC
from re import findall, finditer
from tempfile import TemporaryDirectory, TemporaryFile
from subprocess import run


def resolve_path(path: Union[str, Path]) -> Path:
    if isinstance(path, str):
        return Path(path)
    return path


class _DataType(ABC):
    __slots__ = ('codec', 'bitrate', 'language')

    def __init__(self, codec: str, bitrate: float, language: str):
        assert isinstance(codec, str)
        assert isinstance(bitrate, float)
        assert isinstance(language, str)
        self.codec = codec
        self.bitrate = bitrate
        self.language = language


class Video(_DataType):
    __slots__ = ('resolution', 'fps')

    def __init__(self, codec: str, bitrate: float, language: str, resolution: tuple[int, int], fps: float):
        super().__init__(codec, bitrate, language)
        assert isinstance(resolution, tuple)
        assert isinstance(resolution[0], int)
        assert isinstance(resolution[1], int)
        assert isinstance(fps, float)
        self.resolution = resolution
        self.fps = fps

    def __repr__(self) -> str:
        return f"<Video layer codec={self.codec} fps={self.fps}>"


class Audio(_DataType):
    __slots__ = ('frequency', )

    def __init__(self, codec: str, bitrate: float, language: str, frequency: int):
        super().__init__(codec, bitrate, language)
        assert isinstance(frequency, int)
        self.frequency = frequency

    def __repr__(self) -> str:
        return f"<Audio layer codec={self.codec} frequency={self.frequency}>"


def info_parse(info: str) -> tuple[list[Video], list[Audio]]:
    output = ([], [])
    for line in findall(r'Stream #0:(\d)\[0x\d]\((\w+)\): (Video|Audio): (\w+) [^,]*(.+)', info):
        language = line[1]
        codec = line[3]
        bitrate = float(next(finditer(r' (\d+) kb/s', line[4])).group(1))
        if line[2] == 'Video':
            resolution = next(finditer(r'(\d+)x(\d+)', line[4]))
            resolution = resolution.groups()
            resolution = (int(resolution[0]), int(resolution[1]))
            fps = float(next(finditer(r'(\d+) fps', line[4])).group(1))
            output[0].append(Video(
                codec=codec,
                bitrate=bitrate,
                language=language,
                resolution=resolution,
                fps=fps
            ))
            # output.append(Video(
            #     codec=line[3],
            #     language=line[1],
            #
            # ))
        elif line[2] == 'Audio':
            frequency = int(next(finditer(r' (\d+) Hz', line[4])).group(1))
            output[1].append(Audio(
                codec=codec,
                bitrate=bitrate,
                language=language,
                frequency=frequency
            ))
        else:
            raise RuntimeError()
    return output


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
            raise ValueError('FFMpeg is not correct:', e)

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

    def get_info(self, path: Union[str, Path]):
        path = resolve_path(path)
        if not path.exists():
            raise ValueError('Path is not correct')
        if not path.is_file():
            raise ValueError('Path target is not a files')
        return info_parse(self._call_ffmpeg(f'-i "{path}"'))

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

    def extract_audio(self, video_source: Union[str, Path]) -> Path:
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
        return target_aac

    def aac_to_wav(self, audio_source: Union[str, Path]) -> Path:
        audio_source = resolve_path(audio_source)
        if not audio_source.exists():
            raise ValueError('Path is not correct')
        if not audio_source.is_file():
            raise ValueError('Path target is not a files')

        # Transcode to wav
        target_wav = self._tempDirectory_path / f"{audio_source.name.split('.')[0]}.wav"
        self._call_ffmpeg(f'-i "{audio_source}" "{target_wav}"')

        return target_wav

    def wav_to_aac(self, audio_source: Union[str, Path]) -> Path:
        audio_source = resolve_path(audio_source)
        if not audio_source.exists():
            raise ValueError('Path is not correct')
        if not audio_source.is_file():
            raise ValueError('Path target is not a files')

        # Transcode to wav
        target_aac = self._tempDirectory_path / f"{audio_source.name.split('.')[0]}.aac"
        self._call_ffmpeg(f'-i "{audio_source}" "{target_aac}"')

        return target_aac

    def get_wav(
            self,
            video_source: Union[Path, str]
    ) -> Path:
        video_source = resolve_path(video_source)

        if not video_source.exists():
            raise ValueError('Path is not correct')
        if not video_source.is_file():
            raise ValueError('Path target is not a files')

        aac_file = self.extract_audio(video_source)
        wav_file = self.aac_to_wav(aac_file)
        return wav_file

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
        changer(wav)
        new_video = self.replace_audio_line(video_source, wav, use_tempdir=True)
        if replace:
            video_source.unlink()
            new_video.rename(video_source.absolute())
        else:
            name = video_source.name
            index = name.rfind('.')
            name = name[:index] + '_replaced' + name[index:]
            new_video.rename(video_source.absolute().parent / name)


def main():
    with FFMpeg(r'bin/ffmpeg.exe') as ffmpeg:
        ffmpeg.edit_video('ыф.mp4', lambda x: print(x), replace=False)


if __name__ == '__main__':
    main()
