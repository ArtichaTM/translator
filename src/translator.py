from typing import Union
from collections.abc import Iterable
from logging import warning

from argostranslate.translate import get_translation_from_codes, ITranslation
from argostranslate.package import get_installed_packages


__all__ = (
    'NoSuchLanguage',
    'Translator'
)


class NoSuchLanguage(Exception):
    pass


class Translator:
    """Singleton to translate from Russian to other languages
    Supported direct translation from Russian to English
    Other supported only as transit via English
    """
    __slots__ = ('_direct_map', '_transit_map')
    __instance = None

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def __init__(self):
        self._direct_map: dict[str, ITranslation] = dict()
        self._transit_map: dict[str, ITranslation] = dict()
        for package in get_installed_packages():
            transl_package = get_translation_from_codes(package.from_code, package.to_code)
            if package.from_code == 'ru':
                self._direct_map[package.to_code] = transl_package
            elif package.from_code == 'en':
                self._transit_map[package.to_code] = transl_package
        self._transit_map.pop('ru')

    def __call__(self, values: Union[str, Iterable[str]], target: str) -> Union[str, list[str]]:
        """ High-level translation
        If values is type of string, returns translated string
        If values iterable, returns list of translated strings
        :param values: string or iterable of strings
        :param target: code of target language
        :return: string, or list of strings, based on the values argument type
        """
        if isinstance(values, str):
            return self.translate(values, target)
        if isinstance(values, Iterable):
            return self.translate_list(values, target)

    def translate(self, string: str, target: str) -> str:
        """ Translates from one language to another
        :param string: String that needs to be translated
        :param target: Code of target language: en, ru, esp, etc...
        :return: Translated string

        Assumes that code of target language is correct
        """
        if target in self._direct_map:
            return self._direct_map[target].translate(string)
        elif target in self._transit_map:
            en_string = self._direct_map['en'].translate(string)
            return self._transit_map[target].translate(en_string)
        else:
            raise ValueError('No such language')

    def translate_list(self, strings: Iterable[str], target: str) -> list[str]:
        """ Translates list of strings from one language to another
        :param strings: List of strings that needs to be translated
        :param target: Code of target language: en, ru, esp, etc...
        :return: Translated list of strings

        Assumes that code of target language is correct
        Assumes that length of input and output list equals
        """
        output = []
        for i in strings:
            output.append(self.translate(i, target))
        return output

    @classmethod
    def init(cls) -> None:
        if cls.__instance is None:
            Translator()
        else:
            warning('Trying to init() class Translator while instance already exists')

    def available_codes(self) -> list[str]:
        return sorted([*self._direct_map.keys(), *self._transit_map.keys()])
