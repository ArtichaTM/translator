from pathlib import Path
from typing import Generator, Iterable, Union


__all__ = ('Line', 'subtitles_write')


class Line:
    __slots__ = ('start', 'end', 'text')

    def __init__(self, start: float, end: float, text: str):
        assert isinstance(start, (int, float))
        assert isinstance(end, (int, float))
        assert isinstance(text, str)
        self.start = start
        self.end = end
        self.text = text

    @staticmethod
    def float_to_srt_time(value: float) -> str:
        microsecnds = int((value % 1) * 1000)
        seconds = int(value % 60)
        minutes = int(value // 60)
        hours = int(minutes // 60)
        minutes = minutes % 60
        return f"{hours:02.0f}:{minutes:02.0f}:{seconds:02.0f},{microsecnds:03.0f}"

    def as_srt_line(self) -> list[str]:
        return [
            f'{self.float_to_srt_time(self.start)} --> {self.float_to_srt_time(self.end)}',
            f'{self.text}'
        ]


def subtitles_write(path: Union[str, Path] = 'sub.srt') -> Generator[int, Union[Iterable[Line], Line], None]:
    if isinstance(path, str):
        if not path.endswith('.srt'):
            path = path + '.str'
        path = Path(path)
    elif isinstance(path, Path):
        if not path.name.endswith('.srt'):
            path = path.parent / (path.name.split('.')[0] + '.str')
    else:
        assert False

    counter = 1
    with path.open(mode='w', encoding='utf-8') as f:
        while True:
            text: Union[Iterable[Line], Line] = yield counter
            if isinstance(text, Line):
                f.write('\n'.join([
                    str(counter),
                    *text.as_srt_line(),
                    '\n'
                ]))
                counter += 1
            else:
                for line in text:
                    assert isinstance(line, Line)
                    f.write('\n'.join([
                        str(counter),
                        *line.as_srt_line(),
                        '\n'
                    ]))
                    counter += 1


def main():
    xz = subtitles_write('subls.srt')
    next(xz)
    xz.send(Line(20, 30, 'Привет'))
    xz.send([
        Line(33, 40, 'Как твои дела?'),
        Line(44, 50, 'Ты крутой?')
    ])


if __name__ == '__main__':
    main()
