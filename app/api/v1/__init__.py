"""
sokoraAPI V1
==========

sokoraAPIエンドポイントのバージョン1です。
"""

# APIバージョン
__version__ = "0.1.0"

# モジュールのインポート
# ページ・UI関連
from . import pages
# データ操作API関連
from . import attendance, location, user
