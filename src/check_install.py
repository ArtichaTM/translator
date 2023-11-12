from pathlib import Path

from argostranslate import package
from TTS.api import TTS


def update() -> None:
    """
    Downloads available languages for argostranslate
    to translate from Russian to ANY available
    """
    print('Checking ArgosTranslate packages')
    package.update_package_index()
    packages_available = package.get_available_packages()
    packages_installed = package.get_installed_packages()

    print('Downloading ru -> Any')
    for language_package in packages_available:
        if language_package.from_code != 'ru':
            continue
        elif language_package in packages_installed:
            print(f'\tPackage {language_package} already installed')
            continue
        print(f'\tDownloading language pack {language_package}')
        downloaded = language_package.download()
        print('\tInstalling...')
        package.install_from_path(downloaded)

    print('Downloading en -> Any for translations ru -> en -> Any')
    for language_package in packages_available:
        if language_package.from_code != 'en':
            continue
        elif language_package in packages_installed:
            print(f'\tPackage {language_package} already installed')
            continue
        print(f'\tDownloading language pack {language_package}')
        downloaded = language_package.download()
        print('\tInstalling...')
        package.install_from_path(downloaded)

    print('Checking coqui-ai package')
    mm_path = Path('bin/cqoui.pth')
    if not mm_path.parent.exists():
        mm_path.mkdir(parents=True)
    if not mm_path.exists():
        mm_path.touch(exist_ok=True)
    TTS("tts_models/multilingual/multi-dataset/bark")
    TTS("tts_models/multilingual/multi-dataset/xtts_v2")


if __name__ == '__main__':
    update()
