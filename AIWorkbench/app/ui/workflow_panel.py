"""工作流面板：创建、编辑、运行多步骤工作流。"""

from __future__ import annotations

import uuid
from datetime import datetime

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..api_client import APIClient, APIError
from ..workflow import Workflow, WorkflowManager, suggest_workflow_presets
from .widgets import show_toast


class WorkflowRunner(QThread):
    """在后台线程逐步执行工作流，避免阻塞 UI。"""

    step_finished = pyqtSignal(int, str)   # index, output
    step_failed = pyqtSignal(int, str)     # index, error
    finished_all = pyqtSignal(list)        # 所有步骤输出

    def __init__(self, workflow: Workflow, user_input: str) -> None:
        super().__init__()
        self.workflow = workflow
        self.user_input = user_input
        self.outputs: list[str] = []

    def run(self) -> None:
        client = APIClient()
        for i, step in enumerate(self.workflow.steps):
            context = self.outputs[-1] if self.outputs and step.use_previous else self.user_input
            prompt = step.prompt.replace("{INPUT}", context)
            messages = [{"role": "user", "content": prompt}]
            try:
                result = client.chat_text(messages)
            except APIError as exc:
                self.step_failed.emit(i, str(exc))
                break
            except Exception as exc:  # noqa: BLE001
                self.step_failed.emit(i, str(exc))
                break
            self.outputs.append(result)
            self.step_finished.emit(i, result)
        self.finished_all.emit(self.outputs)


class WorkflowPanel(QWidget):
    def __init__(self, db, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.manager = WorkflowManager()
        self.current: Workflow | None = None
        self._ensure_presets()
        self._build_ui()
        self.refresh()

    def _ensure_presets(self) -> None:
        existing = self.manager.list_workflows()
        if existing:
            return
        for w in suggest_workflow_presets():
            if self.manager.get(w.id) is None:
                w.created_at = datetime.now().isoformat(timespec="seconds")
                self.manager.save(w)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        title = QLabel("工作流")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        splitter = QSplitter()
        splitter.addWidget(self._build_list())
        splitter.addWidget(self._build_editor())
        splitter.setSizes([150, 400])
        layout.addWidget(splitter, 1)

        self.input_edit = QPlainTextEdit()
        self.input_edit.setPlaceholderText("在这里输入工作流的起始内容…")
        self.input_edit.setFixedHeight(70)
        layout.addWidget(QLabel("输入："))
        layout.addWidget(self.input_edit)

        run_row = QHBoxLayout()
        run_btn = QPushButton("▶ 运行工作流")
        run_btn.setObjectName("accentBtn")
        run_btn.clicked.connect(self.run_workflow)
        self.output_edit = QPlainTextEdit()
        self.output_edit.setReadOnly(True)
        run_row.addWidget(run_btn)
        run_row.addStretch(1)
        layout.addLayout(run_row)
        layout.addWidget(QLabel("输出："))
        layout.addWidget(self.output_edit, 1)

        self.run_btn = run_btn

    def _build_list(self) -> QWidget:
        box = QWidget()
        col = QVBoxLayout(box)
        col.setContentsMargins(0, 0, 0, 0)
        self.workflow_list = QListWidget()
        col.addWidget(self.workflow_list, 1)

        row = QHBoxLayout()
        new_btn = QPushButton("新建")
        new_btn.clicked.connect(self.new_workflow)
        del_btn = QPushButton("删除")
        del_btn.clicked.connect(self.delete_workflow)
        row.addWidget(new_btn)
        row.addWidget(del_btn)
        col.addLayout(row)

        self.workflow_list.currentRowChanged.connect(self._on_select)
        return box

    def _build_editor(self) -> QWidget:
        box = QWidget()
        col = QVBoxLayout(box)
        col.setContentsMargins(0, 0, 0, 0)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("工作流名称")
        col.addWidget(self.name_edit)

        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("描述")
        col.addWidget(self.desc_edit)

        col.addWidget(QLabel("步骤（每行一步，{INPUT} 代表上一步输出）："))
        self.steps_edit = QPlainTextEdit()
        self.steps_edit.setPlaceholderText("步骤1\n步骤2\n…")
        col.addWidget(self.steps_edit, 1)

        save_row = QHBoxLayout()
        self.save_btn = QPushButton("保存")
        self.save_btn.setObjectName("accentBtn")
        self.save_btn.clicked.connect(self.save_workflow)
        save_row.addWidget(self.save_btn)
        save_row.addStretch(1)
        col.addLayout(save_row)
        return box

    # ------------------------------------------------------------------ 数据
    def refresh(self) -> None:
        self.workflow_list.blockSignals(True)
        self.workflow_list.clear()
        for w in self.manager.list_workflows():
            self.workflow_list.addItem(w.name)
        self.workflow_list.blockSignals(False)
        if self.workflow_list.count():
            self.workflow_list.setCurrentRow(0)
        else:
            self.current = None
            self._clear_editor()

    def _on_select(self, row: int) -> None:
        workflows = self.manager.list_workflows()
        if 0 <= row < len(workflows):
            self.current = workflows[row]
            self.name_edit.setText(self.current.name)
            self.desc_edit.setText(self.current.description)
            self.steps_edit.setPlainText("\n".join(s.prompt for s in self.current.steps))

    def _clear_editor(self) -> None:
        self.name_edit.clear()
        self.desc_edit.clear()
        self.steps_edit.clear()

    # ------------------------------------------------------------------ 动作
    def new_workflow(self) -> None:
        name, ok = QInputDialog.getText(self, "新建工作流", "名称:")
        if not ok or not name.strip():
            return
        wf = Workflow(
            id=uuid.uuid4().hex[:12],
            name=name.strip(),
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        self.manager.save(wf)
        self.refresh()
        for row in range(self.workflow_list.count()):
            if self.workflow_list.item(row).text() == wf.name:
                self.workflow_list.setCurrentRow(row)
                break
        show_toast(self, "工作流已创建")

    def save_workflow(self) -> None:
        if self.current is None:
            show_toast(self, "请先选择或新建一个工作流", success=False)
            return
        self.current.name = self.name_edit.text().strip() or self.current.name
        self.current.description = self.desc_edit.text().strip()
        prompts = [line for line in self.steps_edit.toPlainText().splitlines() if line.strip()]
        self.current.steps = []
        for i, p in enumerate(prompts, 1):
            from ..workflow import WorkflowStep

            self.current.steps.append(WorkflowStep(name=f"步骤{i}", prompt=p))
        self.manager.save(self.current)
        self.refresh()
        show_toast(self, "工作流已保存")

    def delete_workflow(self) -> None:
        row = self.workflow_list.currentRow()
        if row < 0:
            show_toast(self, "请先选择一个工作流", success=False)
            return
        workflows = self.manager.list_workflows()
        ret = QMessageBox.question(self, "删除工作流", f"确定删除「{workflows[row].name}」吗？")
        if ret == QMessageBox.StandardButton.Yes:
            self.manager.delete(workflows[row].id)
            self.refresh()
            show_toast(self, "已删除工作流")

    def run_workflow(self) -> None:
        if self.current is None:
            show_toast(self, "请先选择或新建一个工作流", success=False)
            return
        if not self.current.steps:
            show_toast(self, "该工作流还没有步骤", success=False)
            return
        user_input = self.input_edit.toPlainText().strip()
        if not user_input:
            show_toast(self, "请先输入工作流起始内容", success=False)
            return

        self.output_edit.clear()
        self.run_btn.setEnabled(False)
        self.run_btn.setText("运行中…")
        self.runner = WorkflowRunner(self.current, user_input)
        self.runner.step_finished.connect(self._on_step_finished)
        self.runner.step_failed.connect(self._on_step_failed)
        self.runner.finished_all.connect(self._on_finished)
        self.runner.start()

    def _on_step_finished(self, index: int, output: str) -> None:
        self.output_edit.appendPlainText(f"———— 步骤 {index + 1} 完成 ————\n{output}\n")

    def _on_step_failed(self, index: int, error: str) -> None:
        self.output_edit.appendPlainText(f"步骤 {index + 1} 失败：{error}\n")
        self._reset_run_state()

    def _on_finished(self, outputs: list) -> None:
        if outputs and self.current:
            self.output_edit.appendPlainText("==== 最终结果 ====")
            self.output_edit.appendPlainText(outputs[-1])
        self._reset_run_state()

    def _reset_run_state(self) -> None:
        self.run_btn.setEnabled(True)
        self.run_btn.setText("▶ 运行工作流")