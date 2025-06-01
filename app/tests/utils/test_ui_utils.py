"""
ui_utils のテストケース
"""

import pytest
from typing import List, Dict, Any

from app.utils.ui_utils import (
    _get_color_for_index, get_location_color_classes, _map_locations,
    generate_location_styles, generate_location_badges, generate_location_data,
    has_data_for_day, TAILWIND_COLORS, LocationBase, LocationData
)


class TestGetColorForIndex:
    """_get_color_for_index関数のテスト"""

    def test_get_color_for_index_normal(self) -> None:
        """_get_color_for_index関数のテスト（通常ケース）"""
        # TAILWIND_COLORSが7個の色を持つ前提
        assert _get_color_for_index(0) == "success"
        assert _get_color_for_index(1) == "primary"
        assert _get_color_for_index(2) == "warning"

    def test_get_color_for_index_wrap_around(self) -> None:
        """_get_color_for_index関数のテスト（ラップアラウンド）"""
        # 7個の色があるので、7は0と同じ
        color_count = len(TAILWIND_COLORS)
        assert _get_color_for_index(0) == _get_color_for_index(color_count)
        assert _get_color_for_index(1) == _get_color_for_index(color_count + 1)

    def test_get_color_for_index_negative(self) -> None:
        """_get_color_for_index関数のテスト（負のインデックス）"""
        # 負のインデックスでも適切に色が返される
        result = _get_color_for_index(-1)
        assert result in TAILWIND_COLORS

    def test_get_color_for_index_large_number(self) -> None:
        """_get_color_for_index関数のテスト（大きな数値）"""
        result = _get_color_for_index(100)
        assert result in TAILWIND_COLORS


class TestGetLocationColorClasses:
    """get_location_color_classes関数のテスト"""

    def test_get_location_color_classes_valid_id(self) -> None:
        """get_location_color_classes関数のテスト（有効なID）"""
        result = get_location_color_classes(1)
        
        assert "text_class" in result
        assert "bg_class" in result
        assert result["text_class"] == "text-primary"
        assert result["bg_class"] == "bg-primary/15"

    def test_get_location_color_classes_zero_id(self) -> None:
        """get_location_color_classes関数のテスト（ID=0）"""
        result = get_location_color_classes(0)
        
        assert result["text_class"] == "text-success"
        assert result["bg_class"] == "bg-success/15"

    def test_get_location_color_classes_none_id(self) -> None:
        """get_location_color_classes関数のテスト（ID=None）"""
        result = get_location_color_classes(None)
        
        assert result["text_class"] == "text-success"
        assert result["bg_class"] == "bg-success/15"

    def test_get_location_color_classes_large_id(self) -> None:
        """get_location_color_classes関数のテスト（大きなID）"""
        result = get_location_color_classes(10)
        
        assert "text_class" in result
        assert "bg_class" in result
        assert result["text_class"].startswith("text-")
        assert result["bg_class"].endswith("/15")


class TestMapLocations:
    """_map_locations関数のテスト"""

    def test_map_locations_simple_transform(self) -> None:
        """_map_locations関数のテスト（シンプルな変換）"""
        location_types = ["オフィス", "リモート"]
        
        def transform_fn(loc_type: str, color: str) -> Any:
            return {"name": loc_type, "color": color}
        
        result = _map_locations(location_types, transform_fn)
        
        assert len(result) == 2
        assert result[0]["name"] == "オフィス"
        assert result[0]["color"] == "success"
        assert result[1]["name"] == "リモート"
        assert result[1]["color"] == "primary"

    def test_map_locations_empty_list(self) -> None:
        """_map_locations関数のテスト（空のリスト）"""
        def transform_fn(loc_type: str, color: str) -> Any:
            return {"name": loc_type, "color": color}
        
        result = _map_locations([], transform_fn)
        assert result == []


class TestGenerateLocationStyles:
    """generate_location_styles関数のテスト"""

    def test_generate_location_styles_normal(self) -> None:
        """generate_location_styles関数のテスト（通常ケース）"""
        location_types = ["オフィス", "リモート", "外出"]
        
        result = generate_location_styles(location_types)
        
        assert len(result) == 3
        assert result["オフィス"] == "text-success"
        assert result["リモート"] == "text-primary"
        assert result["外出"] == "text-warning"

    def test_generate_location_styles_empty(self) -> None:
        """generate_location_styles関数のテスト（空のリスト）"""
        result = generate_location_styles([])
        assert result == {}

    def test_generate_location_styles_single_item(self) -> None:
        """generate_location_styles関数のテスト（単一項目）"""
        result = generate_location_styles(["オフィス"])
        
        assert len(result) == 1
        assert result["オフィス"] == "text-success"


class TestGenerateLocationBadges:
    """generate_location_badges関数のテスト"""

    def test_generate_location_badges_normal(self) -> None:
        """generate_location_badges関数のテスト（通常ケース）"""
        location_types = ["オフィス", "リモート"]
        
        result = generate_location_badges(location_types)
        
        assert len(result) == 2
        assert result[0]["name"] == "オフィス"
        assert result[0]["badge"] == "success"
        assert result[1]["name"] == "リモート"
        assert result[1]["badge"] == "primary"

    def test_generate_location_badges_empty(self) -> None:
        """generate_location_badges関数のテスト（空のリスト）"""
        result = generate_location_badges([])
        assert result == []

    def test_generate_location_badges_type_check(self) -> None:
        """generate_location_badges関数のテスト（型チェック）"""
        location_types = ["オフィス"]
        result = generate_location_badges(location_types)
        
        # LocationBase型の構造を確認
        assert "name" in result[0]
        assert "badge" in result[0]
        assert len(result[0]) == 2  # nameとbadgeのみ


class TestGenerateLocationData:
    """generate_location_data関数のテスト"""

    def test_generate_location_data_normal(self) -> None:
        """generate_location_data関数のテスト（通常ケース）"""
        location_types = ["オフィス", "リモート"]
        
        result = generate_location_data(location_types)
        
        assert len(result) == 2
        
        # 1番目の項目
        assert result[0]["name"] == "オフィス"
        assert result[0]["color"] == "text-success"
        assert result[0]["key"] == "オフィス"
        assert result[0]["badge"] == "success"
        
        # 2番目の項目
        assert result[1]["name"] == "リモート"
        assert result[1]["color"] == "text-primary"
        assert result[1]["key"] == "リモート"
        assert result[1]["badge"] == "primary"

    def test_generate_location_data_empty(self) -> None:
        """generate_location_data関数のテスト（空のリスト）"""
        result = generate_location_data([])
        assert result == []

    def test_generate_location_data_type_check(self) -> None:
        """generate_location_data関数のテスト（型チェック）"""
        location_types = ["オフィス"]
        result = generate_location_data(location_types)
        
        # LocationData型の構造を確認
        assert "name" in result[0]
        assert "color" in result[0]
        assert "key" in result[0]
        assert "badge" in result[0]
        assert len(result[0]) == 4  # 4つのフィールド

    def test_generate_location_data_many_items(self) -> None:
        """generate_location_data関数のテスト（多数の項目）"""
        location_types = ["オフィス", "リモート", "外出", "出張", "休暇", "会議", "研修", "その他"]
        
        result = generate_location_data(location_types)
        
        assert len(result) == 8
        
        # 色のラップアラウンドをテスト
        assert result[0]["badge"] == result[7]["badge"]  # 0番目と7番目は同じ色（7色なので）


class TestHasDataForDay:
    """has_data_for_day関数のテスト"""

    def test_has_data_for_day_with_data(self) -> None:
        """has_data_for_day関数のテスト（データあり）"""
        day_data = {
            "オフィス": ["user1", "user2"],
            "リモート": ["user3"]
        }
        
        result = has_data_for_day(day_data)
        assert result is True

    def test_has_data_for_day_empty_lists(self) -> None:
        """has_data_for_day関数のテスト（空のリスト）"""
        day_data: Dict[str, List[str]] = {
            "オフィス": [],
            "リモート": []
        }
        
        result = has_data_for_day(day_data)
        assert result is False

    def test_has_data_for_day_empty_dict(self) -> None:
        """has_data_for_day関数のテスト（空の辞書）"""
        day_data: Dict[str, List] = {}
        
        result = has_data_for_day(day_data)
        assert result is False

    def test_has_data_for_day_mixed_data(self) -> None:
        """has_data_for_day関数のテスト（混在データ）"""
        day_data = {
            "オフィス": [],
            "リモート": ["user1"],
            "外出": []
        }
        
        result = has_data_for_day(day_data)
        assert result is True

    def test_has_data_for_day_single_empty_key(self) -> None:
        """has_data_for_day関数のテスト（単一の空キー）"""
        day_data: Dict[str, List[str]] = {
            "オフィス": []
        }
        
        result = has_data_for_day(day_data)
        assert result is False 