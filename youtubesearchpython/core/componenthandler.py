from typing import Union, List

def getValue(source: dict, path: List[Union[str, int]]) -> Union[str, int, dict, list, None]:
    value = source
    for key in path:
        if isinstance(value, dict) and isinstance(key, str):
            if key in value:
                value = value[key]
            else:
                return None
        elif isinstance(value, list) and isinstance(key, int):
            if 0 <= key < len(value):
                value = value[key]
            else:
                return None
        else:
            return None
    return value


def getVideoId(videoLink: str) -> str:
    if 'youtu.be' in videoLink:
        if videoLink[-1] == '/':
            return videoLink.split('/')[-2]
        return videoLink.split('/')[-1]
    elif 'youtube.com' in videoLink:
        if '&' not in videoLink:
            return videoLink[videoLink.index('v=') + 2:]
        return videoLink[videoLink.index('v=') + 2: videoLink.index('&')]
    else:
        return videoLink

