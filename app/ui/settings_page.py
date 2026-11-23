"""Settings / about page."""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..core.paths import PROJECT_ROOT, SAMPLE_ACCOUNT, TIER_DIR, read_json
from ..core.ratings import Evaluation
from ..core.favorites import get_favorites
from ..core.ratings_io import (
    LOCAL_FILES,
    bundle_path_from_file,
    export_bundle,
    import_bundle,
    reset_local_ratings,
)
from ..state import AppState
from .theme import BORDER, GOLD, MUTED, PANEL_2, TEXT, TEXT_SOFT
from .widgets import rgba


class SettingsPage(QWidget):
    def __init__(self, state: AppState, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        root.addWidget(scroll)
        canvas = QWidget()
        scroll.setWidget(canvas)
        layout = QVBoxLayout(canvas)
        layout.setContentsMargins(28, 20, 28, 28)
        layout.setSpacing(14)

        self.account_card = self._card("当前账号", "载入后会显示来源与保存位置")
        self.account_body = QLabel()
        self.account_body.setStyleSheet(f"color: {TEXT_SOFT}; font-size: 13px;")
        self.account_body.setWordWrap(True)
        self.account_card.layout().addWidget(self.account_body)
        layout.addWidget(self.account_card)

        paths = self._card("路径", "游戏与数据目录")
        self.paths_body = QLabel()
        self.paths_body.setStyleSheet(f"color: {TEXT_SOFT}; font-size: 13px;")
        self.paths_body.setWordWrap(True)
        paths.layout().addWidget(self.paths_body)
        buttons = QHBoxLayout()
        open_project = QPushButton("打开项目目录")
        open_project.setObjectName("Ghost")
        open_project.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(PROJECT_ROOT))))
        buttons.addWidget(open_project)
        reload_sample = QPushButton("重新载入示例")
        reload_sample.setObjectName("Ghost")
        reload_sample.clicked.connect(self._reload_sample)
        buttons.addWidget(reload_sample)
        buttons.addStretch(1)
        paths.layout().addLayout(buttons)
        layout.addWidget(paths)

        scoring = self._card("评分口径", "四维权重与等级")
        scoring_body = QLabel(
            "人形 40% · 妖精 20% · 融合势力 20% · 装备 20%。\n\n"
            "人形：三体人 SS、常用好手 S、可用但不是必须 A-、食之无味 / 上位替代 B、"
            "数值不够 / 特化解 / 未来可期 / 打靶战区 C、生产资料 Sp。\n"
            "妖精：T0 SS、T1 S、T2 A、T3/T4/特殊用途 C。\n"
            "融合势力：最上方稻草人 SS，其余按图内层级归并为 A / B / C。\n"
            "装备：只比较「装备需求一图流」的目标个数与当前个数，按配件 35% / 子弹 40% / 人形 25% 加权。"
        )
        scoring_body.setStyleSheet(f"color: {TEXT_SOFT}; font-size: 13px; line-height: 1.6;")
        scoring_body.setWordWrap(True)
        scoring.layout().addWidget(scoring_body)
        layout.addWidget(scoring)

        extraction = self._card("账号提取", "为什么不直接读本地文件")
        extraction_body = QLabel(
            "账号配置保存在服务器，本地没有完整仓库存档；切换账号后本地缓存也不可靠。\n\n"
            "本工具优先使用游戏自带的 XLua 运行时：附身后在 LuaEnv.Tick 主线程执行一次只读 Lua，"
            "读取 CS.GameData.listGun / listFairy / listEquip / listSangvisGun 与 userInfo，"
            "直接序列化为快照，随后立即 detach。\n\n"
            "备选方案是导入之前保存的 JSON 快照；截图 OCR 只作为最后兜底，不在本版本默认启用。"
        )
        extraction_body.setStyleSheet(f"color: {TEXT_SOFT}; font-size: 13px; line-height: 1.6;")
        extraction_body.setWordWrap(True)
        extraction.layout().addWidget(extraction_body)
        layout.addWidget(extraction)

        sources = self._card("数据与榜单来源", "")
        self.sources_body = QLabel()
        self.sources_body.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        self.sources_body.setWordWrap(True)
        sources.layout().addWidget(self.sources_body)
        layout.addWidget(sources)

        ratings = self._card("评分数据（可导入 / 导出）", "档位强度与萌新推荐分开维护")
        ratings_body = QLabel(
            "导出后得到包含人形 / 妖精 / 融合势力全部档位、推荐标记和备注的 JSON。"
            "修改 JSON 后可直接导入，不需要重新打包；导入结果写入本地 "
            "`*.local.json`，不修改内置榜单。"
        )
        ratings_body.setWordWrap(True)
        ratings_body.setStyleSheet(f"color: {TEXT_SOFT}; font-size: 12px;")
        ratings.layout().addWidget(ratings_body)
        self.ratings_status = QLabel()
        self.ratings_status.setWordWrap(True)
        self.ratings_status.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        ratings.layout().addWidget(self.ratings_status)
        rating_buttons = QHBoxLayout()
        export = QPushButton("导出评分 JSON")
        export.setObjectName("Ghost")
        export.clicked.connect(self._export_ratings)
        rating_buttons.addWidget(export)
        load = QPushButton("导入评分 JSON")
        load.setObjectName("Primary")
        load.clicked.connect(self._import_ratings)
        rating_buttons.addWidget(load)
        reset = QPushButton("恢复内置评分")
        reset.setObjectName("Ghost")
        reset.clicked.connect(self._reset_ratings)
        rating_buttons.addWidget(reset)
        rating_buttons.addStretch(1)
        ratings.layout().addLayout(rating_buttons)
        layout.addWidget(ratings)

        favorites = self._card("收藏", "星标单位可筛选，也可导出给其他人截图")
        self.favorites_status = QLabel()
        self.favorites_status.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        favorites.layout().addWidget(self.favorites_status)
        favorite_buttons = QHBoxLayout()
        export_favorites = QPushButton("导出收藏 JSON")
        export_favorites.setObjectName("Ghost")
        export_favorites.clicked.connect(self._export_favorites)
        favorite_buttons.addWidget(export_favorites)
        favorite_buttons.addStretch(1)
        favorites.layout().addLayout(favorite_buttons)
        layout.addWidget(favorites)

        thanks = self._card("致谢", "")
        thanks_body = QLabel(
            "感谢群友 ルネツア. 指出 Mod3 / 剧情人物 codex 的名称与匹配问题，"
            "宁姆格福王朝灵庙的帮助，以及反熵盒afla、秋水Ameth、归海临渊"
            "提供的强度排行、养成方案、装备与组件资料。"
        )
        thanks_body.setStyleSheet(f"color: {TEXT_SOFT}; font-size: 12px;")
        thanks_body.setWordWrap(True)
        thanks.layout().addWidget(thanks_body)
        layout.addWidget(thanks)
        layout.addStretch(1)

    # ------------------------------------------------------------------
    def _card(self, title: str, subtitle: str) -> QFrame:
        card = QFrame()
        card.setObjectName("Panel")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 15, 18, 16)
        card_layout.setSpacing(8)
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {TEXT}; font-size: 15px; font-weight: 600;")
        card_layout.addWidget(title_label)
        if subtitle:
            sub = QLabel(subtitle)
            sub.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
            card_layout.addWidget(sub)
        return card

    def _export_ratings(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出评分 JSON",
            str(PROJECT_ROOT / "ratings_export.json"),
            "JSON (*.json);;所有文件 (*.*)",
        )
        if not path:
            return
        target = Path(path)
        if target.suffix.lower() != ".json":
            target = target.with_suffix(".json")
        try:
            target.write_text(
                json.dumps(export_bundle(), ensure_ascii=False, indent=1),
                encoding="utf-8",
            )
        except OSError as exc:
            QMessageBox.warning(self, "导出失败", str(exc))
            return
        QMessageBox.information(self, "导出完成", f"评分 JSON 已保存：\n{target}")

    def _import_ratings(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "导入评分 JSON",
            str(PROJECT_ROOT),
            "JSON (*.json);;所有文件 (*.*)",
        )
        if not path:
            return
        try:
            payload = bundle_path_from_file(Path(path))
            import_bundle(payload)
            self.state.reload_ratings()
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "导入失败", str(exc))
            return
        QMessageBox.information(self, "导入完成", "评分已更新，并已重新计算当前账号。")

    def _reset_ratings(self) -> None:
        answer = QMessageBox.question(
            self,
            "恢复内置评分",
            "删除本地评分覆盖并恢复内置榜单？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        reset_local_ratings()
        self.state.reload_ratings()
        QMessageBox.information(self, "已恢复", "已恢复内置评分。")

    def _export_favorites(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出收藏 JSON",
            str(PROJECT_ROOT / "favorites_export.json"),
            "JSON (*.json);;所有文件 (*.*)",
        )
        if not path:
            return
        target = Path(path)
        if target.suffix.lower() != ".json":
            target = target.with_suffix(".json")
        try:
            target.write_text(
                json.dumps(get_favorites().export_payload(), ensure_ascii=False, indent=1),
                encoding="utf-8",
            )
        except OSError as exc:
            QMessageBox.warning(self, "导出失败", str(exc))
            return
        QMessageBox.information(self, "导出完成", f"收藏已保存：\n{target}")

    def _reload_sample(self) -> None:
        self.state.load_sample()

    def refresh(self, evaluation: Evaluation) -> None:
        favorites = get_favorites()
        self.favorites_status.setText(
            f"已收藏 {favorites.count()} 个单位：人形 {len(favorites.codes('doll'))} / "
            f"妖精 {len(favorites.codes('fairy'))} / 融合势力 {len(favorites.codes('sangvis'))}"
        )
        active = [name for name in LOCAL_FILES.values() if (TIER_DIR / name).is_file()]
        if active:
            self.ratings_status.setText(
                "当前生效：本地覆盖 " + " / ".join(active)
                + "（启动时自动读取；ratings_export.json 不会自动加载，需手动导入）"
            )
        else:
            self.ratings_status.setText(
                "当前生效：内置榜单 app/data/tierlists/*.json（ratings_export.json 不会自动加载）"
            )
        account = evaluation.account
        source = account.source or "未知"
        path = account.source_path or "内置数据"
        vehicles = ", ".join(str(item.get("infoid") or item.get("id")) for item in account.vehicles) or "无"
        self.account_body.setText(
            f"昵称：{account.nickname}\n等级：Lv.{account.level or '—'}\nUID：{account.uid}\n来源：{source}\n"
            f"采集时间：{account.captured_at or '未知'}\n"
            f"载具：{len(account.vehicles)} 台（{vehicles}）\n快照：{path}"
        )
        game_root = "未配置"
        try:
            local_paths = read_json(PROJECT_ROOT.parent / "local_paths.json", {}) or {}
            game_root = local_paths.get("gf1_game_root") or "未配置"
        except Exception:
            pass
        self.paths_body.setText(
            f"项目：{PROJECT_ROOT}\n游戏：{game_root}\n示例快照：{SAMPLE_ACCOUNT}"
        )
        self.sources_body.setText(
            "人形强度榜：烧钱强度表.xlsx + 人形强度榜.jpeg（2026-05-30）\n"
            "妖精强度榜：妖精强度榜.png（2026-03-07，不含联动妖精）\n"
            "融合势力强度榜：铁血强度榜.png\n"
            "装备需求：装备需求一图流.jpeg（2023-05-30）\n"
            "头像：游戏 resourceiconspinehead / resourcefairy / resourceiconenemy 资源包；"
            "缺失时使用 Portrait_showcase 默认立绘上半身裁切或占位图。"
        )
