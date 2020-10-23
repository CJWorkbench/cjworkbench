import datetime
import functools
import io
import re
from typing import Dict, List, NamedTuple, Tuple

import babel
import pytz
from icu import Collator, Locale
from babel.dates import get_timezone_location, get_timezone_gmt
from django.http import HttpRequest, JsonResponse


@functools.lru_cache(1)
def _read_timezone_ids_and_aliases() -> Dict[str, List[str]]:
    """Read ZIC-format file from pytz's tzdata.zi. Output {zone: [aliases]}.

    Spec: https://man7.org/linux/man-pages/man8/zic.8.html#FILES
    """
    # example Zone line:
    # Z Antarctica/Troll 0 - -00 2005 F 12
    # we only care about the
    zone_re = re.compile(r"(?:Z|Zo|Zon|Zone)\s+(?P<zone>[^\s]+)")
    # example Link line:
    # L Asia/Nicosia Europe/Nicosia
    # here, "Asia/Nicosia" is the zone, and "Europe/Nicosia" is the link
    link_re = re.compile(r"(?:L|Li|Lin|Link)\s+(?P<zone>[^\s]+)\s+(?P<alias>[^\s]+)")

    zone_aliases = {}  # mapping from zone to all aliases (includes all zones)
    with pytz.open_resource("tzdata.zi") as bio:
        with io.TextIOWrapper(bio, encoding="ascii") as tio:
            for line in tio.readlines():
                zone_match = zone_re.match(line)
                if zone_match:
                    zone = zone_match.group("zone")
                    if zone not in zone_aliases:
                        if zone in pytz.all_timezones_set:  # ignore "Factory" zone
                            zone_aliases[zone] = []
                link_match = link_re.match(line)
                if link_match:
                    zone = link_match.group("zone")
                    alias = link_match.group("alias")
                    if zone in zone_aliases:
                        zone_aliases[zone].append(alias)
                    else:
                        zone_aliases[zone] = [alias]
    return zone_aliases


class LocalizedTimezone(NamedTuple):
    """Information about a timezone, after being localized to a locale."""

    id: str
    name: str
    aliases: List[str]
    name_sort_key: bytes
    tzinfo: datetime.tzinfo
    locale: babel.Locale


def _localize_timezone(
    zone: str, aliases: List[str], locale: babel.Locale, collator: Collator
) -> LocalizedTimezone:
    tzinfo = pytz.timezone(zone)
    name = get_timezone_location(tzinfo, locale=locale)
    name_sort_key = collator.getSortKey(name)
    return LocalizedTimezone(
        id=zone,
        name=name,
        aliases=aliases,
        name_sort_key=name_sort_key,
        tzinfo=tzinfo,
        locale=locale,
    )


@functools.lru_cache
def _localize_timezones(locale: babel.Locale) -> LocalizedTimezone:
    zones_and_aliases = _read_timezone_ids_and_aliases()
    # locale.language: 'en' or 'en_US'
    collator = Collator.createInstance(Locale.createFromName(locale.language))
    return [
        _localize_timezone(zone, aliases, locale, collator)
        for zone, aliases in zones_and_aliases.items()
    ]


class TimestampedLocalizedTimezone(NamedTuple):
    """A timezone with a name and GMT offset calculated at a moment in time."""

    id: str
    name: str
    offset: str
    aliases: List[str]
    sort_key: Tuple[datetime.timedelta, str]


def _timestamp_localized_timezone(
    tz: LocalizedTimezone, dt: datetime.datetime
) -> TimestampedLocalizedTimezone:
    localized_dt = tz.tzinfo.localize(dt)
    offset = get_timezone_gmt(localized_dt, locale=tz.locale)
    return TimestampedLocalizedTimezone(
        id=tz.id,
        name=tz.name,
        offset=offset,
        aliases=tz.aliases,
        sort_key=(localized_dt.utcoffset(), tz.name_sort_key),
    )


def index(request: HttpRequest) -> JsonResponse:
    """List of { id, offset, name, aliases } timezones.

    Timezones are listed from /usr/share/zoneinfo (the IANA time zone database,
    a.k.a. "tzdata" or "zoneinfo"). They're in the "timezone" key.

    Aliases are important: "America/Buenos_Aires" was a timezone at one point,
    and now it's just an alias for "America/Argentina/Buenos_Aires". Clients
    must be aware of aliases, because a timezone ID selected today may become an
    alias ID tomorrow. That means users may have selected alias IDs.

    Offset and name are formatted according to the request locale. In
    English, it will look like (October 23, 2020):

    - { id: America/St_Johns, offset: GMT-03:30, name: Canada (St. John's) Time }

    The offset is calculated from the _request date_. On January 1, 2020:

    - { id: America/St_Johns, offset: GMT-04:30, name: Canada (St. John's) Time }

    The response is ordered by (offset[numeric], name[locale-collation]).
    """
    # Note that CLDR has a different set of IDs for timezones: "BCP47" IDs.
    # BCP47 IDs and aliases are different from the IANA ones. The IANA ones
    # are The Standard.
    locale = babel.Locale(request.locale_id)
    now = datetime.datetime.utcnow()

    localized_timezones = _localize_timezones(locale)
    timestamped_timezones = [
        _timestamp_localized_timezone(ltz, now) for ltz in localized_timezones
    ]
    timestamped_timezones.sort(key=lambda tz: tz.sort_key)

    json_timezones = [
        {"id": tz.id, "offset": tz.offset, "name": tz.name, "aliases": tz.aliases}
        for tz in timestamped_timezones
    ]
    response = JsonResponse(
        {"locale_id": request.locale_id, "timezones": json_timezones},
        json_dumps_params={"ensure_ascii": False},
    )
    response["Content-Language"] = request.locale_id
    return response
