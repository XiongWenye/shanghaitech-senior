#!/usr/bin/env python3
"""
ShanghaiTech Campus Locations & Geolocation Coordinates Database.
Extracted and enriched from TechPie-flutter's StructuredLocation mapping.

Provides:
- Exact latitude/longitude coordinates for all major academic and campus buildings.
- Keyword matching against classroom strings (e.g. "信息学院1A-200", "教学中心204").
- Geo-URI and Apple structured location vCalendar attribute generators.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple

CAMPUS_NAME = "上海科技大学"
CAMPUS_ADDRESS = "上海市浦东新区中科路1号"
CAMPUS_POSTAL_CODE = "201210"

@dataclass(frozen=True)
class CampusLocation:
    keyword: str
    title: str
    latitude: float
    longitude: float
    alias: Tuple[str, ...] = ()
    description: str = ""

# Official coordinates verified from TechPie-flutter and campus survey
STRUCTURED_LOCATIONS: List[CampusLocation] = [
    CampusLocation(
        keyword="信息学院",
        title="上海科技大学信息科学与技术学院",
        latitude=31.18043,
        longitude=121.59070,
        alias=("SIST", "信息科学与技术学院", "信院", "1A", "1B", "1C"),
        description="信息科学与技术学院楼群 (1A/1B/1C)"
    ),
    CampusLocation(
        keyword="创管学院",
        title="上海科技大学创业与管理学院",
        latitude=31.17872,
        longitude=121.59061,
        alias=("SEM", "创业与管理学院", "创管"),
        description="创业与管理学院大楼"
    ),
    CampusLocation(
        keyword="生命学院",
        title="上海科技大学生命科学与技术学院",
        latitude=31.18180,
        longitude=121.59018,
        alias=("SLST", "生命科学与技术学院", "生院"),
        description="生命科学与技术学院大楼"
    ),
    CampusLocation(
        keyword="物质学院",
        title="上海科技大学物质科学与技术学院",
        latitude=31.17894,
        longitude=121.58821,
        alias=("SPST", "物质科学与技术学院", "物院"),
        description="物质科学与技术学院大楼"
    ),
    CampusLocation(
        keyword="教学中心",
        title="上海科技大学教学中心",
        latitude=31.17772,
        longitude=121.59093,
        alias=("教学楼", "公共教学楼", "教中", "JC"),
        description="公共教学中心大楼"
    ),
    CampusLocation(
        keyword="创艺学院",
        title="上海科技大学创意与艺术学院",
        latitude=31.17887,
        longitude=121.58887,
        alias=("SCA", "创意与艺术学院", "创艺"),
        description="创意与艺术学院大楼"
    ),
    CampusLocation(
        keyword="生医工学院",
        title="上海科技大学生物医学工程学院",
        latitude=31.17997,
        longitude=121.59122,
        alias=("BME", "生物医学工程学院", "生医工"),
        description="生物医学工程学院大楼"
    ),
    CampusLocation(
        keyword="体育馆",
        title="上海科技大学体育馆",
        latitude=31.17645,
        longitude=121.58850,
        alias=("GYM", "网球场", "羽毛球场", "健身房", "匹克球场", "风雨操场", "气膜馆"),
        description="上海科技大学室内体育馆与运动场"
    ),
    CampusLocation(
        keyword="图书馆",
        title="上海科技大学图书馆",
        latitude=31.17942,
        longitude=121.58980,
        alias=("校图书馆", "图文信息中心"),
        description="上海科技大学图书信息中心"
    ),
    CampusLocation(
        keyword="行政中心",
        title="上海科技大学行政中心",
        latitude=31.17698,
        longitude=121.58965,
        alias=("行政楼", "校部"),
        description="行政主楼"
    ),
    CampusLocation(
        keyword="国际交流中心",
        title="上海科技大学国际交流中心",
        latitude=31.17610,
        longitude=121.59250,
        alias=("国交", "会堂", "会议中心"),
        description="会议会堂与国际交流中心"
    ),
]

def find_location(classroom: str) -> Optional[CampusLocation]:
    """
    Match classroom string to a structured campus location.
    Checks main keyword, aliases, and building code abbreviations.
    """
    if not classroom:
        return None
    c_str = classroom.strip().upper()
    
    # 1. First priority: Exact or substring match on keyword
    for loc in STRUCTURED_LOCATIONS:
        if loc.keyword.upper() in c_str:
            return loc
            
    # 2. Second priority: Match aliases
    for loc in STRUCTURED_LOCATIONS:
        for alias in loc.alias:
            if alias.upper() in c_str:
                return loc
                
    return None

def format_apple_structured_location(loc: CampusLocation, radius: int = 200) -> str:
    """
    Generates X-APPLE-STRUCTURED-LOCATION attribute string for iCalendar (.ics).
    Ensures iOS Calendar shows interactive map pins and departure alerts.
    """
    escaped_title = loc.title.replace('\\', '\\\\').replace('"', '\\"')
    escaped_addr = CAMPUS_ADDRESS.replace('\\', '\\\\').replace('"', '\\"')
    return (
        f'X-APPLE-STRUCTURED-LOCATION;VALUE=URI;'
        f'X-ADDRESS="{escaped_addr}";'
        f'X-APPLE-RADIUS={radius};'
        f'X-TITLE="{escaped_title}":geo:{loc.latitude},{loc.longitude}'
    )

def format_geo_attribute(loc: CampusLocation) -> str:
    """Generates standard RFC 5545 GEO coordinate attribute."""
    return f"GEO:{loc.latitude};{loc.longitude}"

if __name__ == "__main__":
    import sys
    query = sys.argv[1] if len(sys.argv) > 1 else "信息学院1A-200"
    loc = find_location(query)
    if loc:
        print(f"✅ 查询: {query}")
        print(f"   建筑: {loc.title} ({loc.keyword})")
        print(f"   坐标: {loc.latitude}, {loc.longitude}")
        print(f"   Apple Geo: {format_apple_structured_location(loc)}")
    else:
        print(f"❌ 未找到匹配建筑: {query}")
