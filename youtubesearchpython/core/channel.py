import copy
import json
from typing import Union, List
from urllib.parse import urlencode
import re

from youtubesearchpython.core.constants import *
from youtubesearchpython.core.requests import RequestCore
from youtubesearchpython.core.componenthandler import getValue, getVideoId


class ChannelCore(RequestCore):
    def __init__(self, channel_id: str, request_params: str):
        super().__init__()
        self.browseId = channel_id
        self.params = request_params
        self.result = {}
        self.continuation = None

    def prepare_request(self):
        self.url = 'https://www.youtube.com/youtubei/v1/browse' + "?" + urlencode({
            'key': searchKey,
            "prettyPrint": "false"
        })
        self.data = copy.deepcopy(requestPayload)
        if not self.continuation:
            self.data["params"] = self.params
            self.data["browseId"] = self.browseId
        else:
            self.data["continuation"] = self.continuation

    def playlist_parse(self, i) -> dict:
        return {
            "id": getValue(i, ["playlistId"]),
            "thumbnails": getValue(i, ["thumbnail", "thumbnails"]),
            "title": getValue(i, ["title", "runs", 0, "text"]),
            "videoCount": getValue(i, ["videoCountShortText", "simpleText"]),
            "lastEdited": getValue(i, ["publishedTimeText", "simpleText"]),
        }

    def parse_response(self):
        response = self.data.json()

        self.result = {
            "id": getValue(response, ["metadata", "channelMetadataRenderer", "externalId"]),
            "url": getValue(response, ["metadata", "channelMetadataRenderer", "channelUrl"]),
            "description": getValue(response, ["metadata", "channelMetadataRenderer", "description"]),
            "title": getValue(response, ["metadata", "channelMetadataRenderer", "title"]),
            "banners": getValue(response, ["header", "pageHeaderRenderer",'content', "pageHeaderViewModel", "banner", "imageBannerViewModel", "image", "sources"]),
            "subscribers":getValue(response,["header", "pageHeaderRenderer", "content", "pageHeaderViewModel","metadata","contentMetadataViewModel","metadataRows",1,"metadataParts",0,"accessibilityLabel"]),
            "thumbnails": getValue(response, ["microformat", "microformatDataRenderer", "thumbnail", "thumbnails"]),
            "availableCountryCodes": getValue(response, ["metadata", "channelMetadataRenderer", "availableCountryCodes"]),
            "isFamilySafe": getValue(response, ["metadata", "channelMetadataRenderer", "isFamilySafe"]),
            "keywords": getValue(response, ["metadata", "channelMetadataRenderer", "keywords"]),
            "tags": getValue(response, ["microformat", "microformatDataRenderer", "tags"]),
        }

        if self.params == ChannelRequestType.Videos:
            self.result.update({"Videos": self.extract_videos_info()})
        elif self.params == ChannelRequestType.playlists:
            self.result.update({"playlists": self.extract_playlists_info()})


    def parse_next_response(self):
        response = self.data.json()

        self.continuation = None

        response = getValue(response, ["onResponseReceivedActions", 0, "appendContinuationItemsAction", "continuationItems"])
        for i in response:
            if getValue(i, ["continuationItemRenderer"]):
                self.continuation = getValue(i, ["continuationItemRenderer", "continuationEndpoint", "continuationCommand", "token"])
                break
            elif getValue(i, ['gridPlaylistRenderer']):
                self.result["playlists"].append(self.playlist_parse(getValue(i, ['gridPlaylistRenderer'])))
            # TODO: Handle other types like gridShowRenderer

    async def async_next(self):
        if not self.continuation:
            return
        self.prepare_request()
        self.data = await self.asyncPostRequest()
        self.parse_next_response()

    def sync_next(self):
        if not self.continuation:
            return
        self.prepare_request()
        self.data = self.syncPostRequest()
        self.parse_next_response()

    def has_more_playlists(self):
        return self.continuation is not None

    async def async_create(self):
        self.prepare_request()
        self.data = await self.asyncPostRequest()
        self.parse_response()

    def sync_create(self):
        self.prepare_request()
        self.data = self.syncPostRequest()
        self.parse_response()

    def prepare_channel_username_request(self):
        self.url = 'https://www.youtube.com/youtubei/v1/navigation/resolve_url?' + urlencode({
            'key': searchKey,
            "prettyPrint": "false"
        })
        self.data = copy.deepcopy(requestPayload)
        self.data['url'] = f"https://www.youtube.com/@{self.browseId.replace('@','')}"

    def parse_channel_username_response(self):
        response = self.data.json()
        if 'endpoint' in response:
            endpoint = response['endpoint']
            if 'browseEndpoint' in endpoint and 'browseId' in endpoint['browseEndpoint']:
                channel_id = endpoint['browseEndpoint']['browseId']
                if channel_id.startswith('UC'):
                    return channel_id

        if 'commandMetadata' in response:
            metadata = response['commandMetadata']
            if 'webCommandMetadata' in metadata:
                web_url = metadata['webCommandMetadata'].get('url', '')
                if '/channel/' in web_url:
                    channel_id = web_url.split('/channel/')[-1].split('/')[0]
                    if channel_id.startswith('UC'):
                        return channel_id

    async def async_get_channel_id(self):
        self.prepare_channel_username_request()
        self.data = await self.asyncPostRequest()
        self.browseId = self.parse_channel_username_response()

    def sync_get_channel_id(self):
        self.prepare_channel_username_request()
        self.data = self.syncPostRequest()
        self.browseId = self.parse_channel_username_response()

    def extract_videos_info(self):
        extracted = []

        for item in getValue(self.data.json(),["contents", "twoColumnBrowseResultsRenderer", "tabs", 1, "tabRenderer","content", "richGridRenderer", "contents"]):
            video_data = getValue(item, ["richItemRenderer", "content", "videoRenderer"])

            video_id = getValue(video_data, ["videoId"])
            title = getValue(video_data, ["title", "runs", 0, "text"])
            duration = getValue(video_data, ["lengthText", "simpleText"])
            duration_accessible = getValue(video_data, ["lengthText", "accessibility", "accessibilityData", "label"])
            views = getValue(video_data, ["viewCountText", "simpleText"])
            short_views = getValue(video_data, ["shortViewCountText", "simpleText"])
            published_time = getValue(video_data, ["publishedTimeText", "simpleText"])
            description = getValue(video_data, ["descriptionSnippet", "runs", 0, "text"])
            thumbnails = getValue(video_data, ["thumbnail", "thumbnails"])
            rich_thumbnail = getValue(video_data, ["richThumbnail", "movingThumbnailRenderer", "movingThumbnailDetails", "thumbnails", 0, "url"])

            video_info = {
                "video_id": video_id,
                "title": title,
                "duration": duration,
                "duration_accessible": duration_accessible,
                "duration_seconds": parse_duration_to_seconds(duration),
                "views": views,
                "views_int": parse_to_int_from_number_string(views),
                "short_views": short_views,
                "published_time": published_time,
                "description": description,
                "thumbnails": thumbnails,
                "rich_thumbnail": rich_thumbnail,
                "watch_url": f"https://www.youtube.com/watch?v={video_id}" if video_id else None
            }

            extracted.append(video_info)

        return extracted[:-1]

    def extract_playlists_info(self):
        extracted = []
        for item in getValue(self.data.json(),["contents","twoColumnBrowseResultsRenderer","tabs",3,"tabRenderer","content","sectionListRenderer","contents",0,"itemSectionRenderer","contents",0,'gridRenderer','items']):
            lockup = getValue(item, ["lockupViewModel"])

            playlist_id = getValue(lockup, ["contentId"])
            title = getValue(lockup, ["metadata", "lockupMetadataViewModel", "title", "content"])

            video_count_text = getValue(lockup,["contentImage", "collectionThumbnailViewModel", "primaryThumbnail", "thumbnailViewModel","overlays", 0, "thumbnailOverlayBadgeViewModel",'thumbnailBadges', 0, "thumbnailBadgeViewModel", "text"])

            video_count = int(re.findall(r'\d+', video_count_text.replace(",", ""))[0]) if video_count_text else 0

            thumbnail = getValue(lockup,["contentImage", "collectionThumbnailViewModel", "primaryThumbnail","thumbnailViewModel", "image", "sources", 0, "url"])

            first_video_id = getValue(lockup,["rendererContext", "commandContext", "onTap", "innertubeCommand", "watchEndpoint", "videoId"])

            url = f"https://www.youtube.com/playlist?list={playlist_id}" if playlist_id else None
            first_watch_url = f"https://www.youtube.com/watch?v={first_video_id}&list={playlist_id}" if playlist_id and first_video_id else None

            playlist_info = {
                "playlist_id": playlist_id,
                "title": title,
                "video_count": video_count,
                "video_count_text": video_count_text,
                "thumbnail": thumbnail,
                "url": url,
                "first_video_id": first_video_id,
                "first_video_watch_url": first_watch_url,
            }
            extracted.append(playlist_info)
        return extracted


def parse_duration_to_seconds(duration: str) -> int:
    if not duration:
        return 0
    parts = duration.split(":")
    parts = [int(p) for p in parts]
    if len(parts) == 3:
        hours, minutes, seconds = parts
    elif len(parts) == 2:
        hours = 0
        minutes, seconds = parts
    elif len(parts) == 1:
        hours = 0
        minutes = 0
        seconds = parts[0]
    else:
        return 0
    return hours * 3600 + minutes * 60 + seconds


def parse_to_int_from_number_string(views_str: str) -> int:
    if not views_str:
        return 0
    digits_only = re.sub(r'[^\d]', '', views_str)
    return int(digits_only) if digits_only else 0
