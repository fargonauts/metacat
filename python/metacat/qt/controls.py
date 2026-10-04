"""The control strip of the Qt GUI: gui.ss's control panel, in the main window.

Metacat is copyright (c) 1999, 2003 by James B. Marshall; this translation is free
software under the GNU General Public License, version 2 or later, like Metacat
itself.  Translated to Python (2026) from gui.ss's make-control-panel, with
metacat/gui/gui.py (its tkinter translation) as a worked translation, for
loop0003 item 05: the run controls.

`QtControlPanel` is gui.ss's control panel object: the same messages (switch-
to-run-mode, switch-to-input-mode, init-new-problem, resume-current-problem,
display-breakpoint-message, ...), with the same effects on the model, and the
widgets of a strip at the top of the main window: the info label, the command
line, the speed slider, Step, Go, Stop and Reset, the breakpoint label and the
self-watching warning.  Enter and the buttons run gui.py's own actions
(go-button-action, ...), which talk to this object through
setup.g_control_panel; the speed slider runs gui.py's speed-slider-action.

The Options menu has the run-control items of gui.ss's Options menu (Set
breakpoint, Clear breakpoint, Step mode interval) and their input dialog;
item 06 adds the rest of the menus and dialogs.

Threads (docs/qt-gui-plan.md 2.5): the engine sends some of these messages
from its own thread (switch-to-run-mode in go, switch-to-input-mode in break,
the breakpoint messages, engine-error).  What touches a widget is posted to
the GUI thread (engine_bridge.GuiInvoker.post) and the message returns at
once; no caller uses the value.  Queries answer from Python attributes.
"""
from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QLineEdit, QMenu, QPushButton,
                               QSlider, QVBoxLayout, QWidget)

from metacat import chez, run, setup, utilities
from metacat.gui import constants as K
from metacat.gui import fonts as gfonts
from metacat.gui import gui, swl
from metacat.objects import SchemeObject, delegate, message, tell
from metacat.qt import fonts
from metacat.qt.canvas import _qcolor
from metacat.qt.engine_bridge import GuiInvoker
from metacat.utilities import base_object, exists_p


def qfont(font):
    """an SWL font (gui/fonts.py's SwlFont) as a QFont"""
    return fonts.qfont(swl.tcl_word(font))


def css_color(color):
    return _qcolor(swl.tcl_word(color)).name()


# --------------------------------------------------------------------------------
# fonts (gui.ss: select-control-panel-fonts)

p_gui_header_font = p_gui_command_line_font = p_gui_run_mode_font = False
p_gui_speed_controls_font = p_gui_speed_controls_italic_font = False
p_gui_input_dialog_font = False


def select_control_panel_fonts():
    """gui.ss: select-control-panel-fonts (the fonts the run controls use)"""
    global p_gui_header_font, p_gui_command_line_font, p_gui_run_mode_font
    global p_gui_speed_controls_font, p_gui_speed_controls_italic_font
    global p_gui_input_dialog_font
    screen = QGuiApplication.primaryScreen()
    screen_height = screen.geometry().height() if screen is not None else 1080
    big = 14 if screen_height > 1024 else 12
    small = 10 if screen_height > 1024 else 8
    ss = gfonts.sans_serif or "helvetica"
    p_gui_header_font = gfonts.swl_font(ss, big, "bold")
    p_gui_command_line_font = gfonts.swl_font(ss, big, "bold")
    p_gui_run_mode_font = gfonts.swl_font(ss, big, "bold", "italic")
    p_gui_speed_controls_font = gfonts.swl_font(ss, small, "bold")
    p_gui_speed_controls_italic_font = gfonts.swl_font(ss, small, "italic")
    p_gui_input_dialog_font = gfonts.swl_font(ss, big, "bold")


# --------------------------------------------------------------------------------
# the input dialog (gui.ss: input-dialog)

class InputDialog(QDialog):
    """gui.ss: input-dialog's toplevel (its field's get-parent)"""

    def raise_(self):
        super().raise_()
        self.activateWindow()


class _InputField:
    """port: the input dialog's SWL <entry>, whose get-parent is the dialog"""

    def __init__(self, dialog, entry):
        self.dialog = dialog
        self.entry = entry

    def get_parent(self):
        return self.dialog

    def set_focus(self):
        self.entry.setFocus()


def input_dialog(x, y, default, message_, input_action, destroy_action):
    """gui.ss: input-dialog.  Enter reads the field: empty closes the dialog,
    a number below 1 or no number shows "Invalid input!" for 700 ms, else
    input_action gets the number and the dialog closes."""
    dialog = InputDialog()
    dialog.setWindowTitle("Input")
    dialog.setAttribute(Qt.WA_DeleteOnClose)
    dialog.setStyleSheet("InputDialog { background: %s; }" % css_color(K.c_white))
    state = {"closed": False}
    message_label = QLabel(message_)
    message_label.setFont(qfont(p_gui_input_dialog_font))
    message_label.setAlignment(Qt.AlignCenter)
    input_field = QLineEdit()
    input_field.setFont(qfont(p_gui_command_line_font))
    input_field.setMaxLength(64)
    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(15, 15, 15, 15)
    layout.addWidget(message_label)
    layout.addSpacing(20)
    layout.addWidget(input_field, 0, Qt.AlignHCenter)
    dialog.setMinimumWidth(230)

    def black():
        message_label.setStyleSheet("color: %s;" % css_color(K.c_black))
    black()

    def destroyed(_result):
        if not state["closed"]:
            state["closed"] = True
            destroy_action(dialog)
    dialog.finished.connect(destroyed)

    def action():
        input_ = input_field.text()
        if input_ == "":
            dialog.close()
            return
        value = chez.string_to_number(input_)
        if value is False or value < 1:
            message_label.setStyleSheet("color: %s;" % css_color(K.c_red))
            message_label.setText("Invalid input!")

            def back():   # port: (pause 700) becomes a timer
                if not state["closed"]:
                    black()
                    message_label.setText(message_)
            QTimer.singleShot(700, back)
        else:
            input_action(value)
            dialog.close()
    input_field.returnPressed.connect(action)
    if exists_p(default):
        input_field.setText(default)
        input_field.selectAll()
    cp = setup.g_control_panel
    frame = tell(cp, "get-widgets")["frame"] if cp else None
    if frame is not None:
        corner = frame.mapToGlobal(frame.rect().topLeft())
        dialog.move(corner.x() + x, corner.y() + y)
    dialog.show()
    input_field.setFocus()
    return _InputField(dialog, input_field)


_breakpoint_input_field = [False]


def set_breakpoint_action(item=None):
    """gui.ss: set-breakpoint-action"""
    if exists_p(_breakpoint_input_field[0]):
        _breakpoint_input_field[0].get_parent().raise_()
        _breakpoint_input_field[0].set_focus()
        return

    def input_action(timestep):
        run.g_break_time = timestep
        tell(setup.g_control_panel, "display-breakpoint-message")

    def destroy(toplevel):
        _breakpoint_input_field[0] = False
        return True
    _breakpoint_input_field[0] = input_dialog(
        20, 80,
        chez.number_to_string(run.g_break_time) if exists_p(run.g_break_time) else "",
        "Enter new breakpoint:", input_action, destroy)


def clear_breakpoint_action(item=None):
    """gui.ss: clear-breakpoint-action"""
    run.g_break_time = False
    tell(setup.g_control_panel, "clear-breakpoint-message")


_step_interval_input_field = [False]


def set_step_interval_action(item=None):
    """gui.ss: set-step-interval-action"""
    if exists_p(_step_interval_input_field[0]):
        _step_interval_input_field[0].get_parent().raise_()
        _step_interval_input_field[0].set_focus()
        return

    def input_action(interval):
        run.p_step_cycles = interval

    def destroy(toplevel):
        _step_interval_input_field[0] = False
        return True
    _step_interval_input_field[0] = input_dialog(
        80, 80, chez.number_to_string(run.p_step_cycles), "Enter new step interval:",
        input_action, destroy)


# --------------------------------------------------------------------------------

def create_slider(parent, text, min_text, max_text, init_val, slide_action):
    """gui.ss: create-slider: the scale over its Slow and Fast labels, and its
    name under them.  Returns the frame and the QSlider."""
    frame = QWidget(parent)
    slider = QSlider(Qt.Horizontal)
    slider.setRange(0, 100)
    slider.setValue(init_val)
    slider.setFixedWidth(gui.p_gui_slider_length + 40)
    slider.valueChanged.connect(lambda value: slide_action(slider, value))
    labels = QHBoxLayout()
    labels.setContentsMargins(0, 0, 0, 0)
    for t, align in ((min_text, Qt.AlignLeft), (text, Qt.AlignCenter), (max_text, Qt.AlignRight)):
        label = QLabel(t)
        label.setFont(qfont(p_gui_speed_controls_font if t == text
                            else p_gui_speed_controls_italic_font))
        labels.addWidget(label, 1, align)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    layout.addWidget(slider)
    layout.addLayout(labels)
    return frame, slider


def make_control_panel(invoker=None):
    """gui.ss: make-control-panel"""
    return QtControlPanel(invoker)


class QtControlPanel(SchemeObject):
    """gui.ss: make-control-panel (the control panel object), as a strip"""

    def __init__(this, invoker=None):
        select_control_panel_fonts()
        gui.load()
        this.invoker = invoker or GuiInvoker()
        this.parked_hook = None       # the main window's sync, when the engine parks
        white = K.c_white
        strip = QWidget()
        strip.setObjectName("control-strip")
        strip.setAutoFillBackground(True)
        strip.setStyleSheet("QWidget#control-strip { background: %s; }" % css_color(white))
        info_label = QLabel("Please enter a problem:")
        info_label.setFont(qfont(p_gui_header_font))
        info_label.setMinimumWidth(330)
        command_line = QLineEdit()
        command_line.setMinimumWidth(380)
        this.command_line_action = gui.go_button_action
        command_line.returnPressed.connect(lambda: this.command_line_action(command_line))
        speed_controls = QWidget()
        speed_controls.setObjectName("speed-controls")
        speed_controls.setStyleSheet("QWidget#speed-controls { background: %s; }"
                                     % css_color(K.p_gui_speed_controls_color))
        slider_frame, speed_slider = create_slider(speed_controls, "Speed", "Slow", "Fast",
                                                   gui.p_initial_speed, gui.speed_slider_action)

        def button(title, action):
            b = QPushButton(title)
            b.setFont(qfont(p_gui_speed_controls_font))
            b.setEnabled(False)
            b.clicked.connect(lambda: action(b))
            return b
        step_button = button("Step", gui.step_button_action)
        go_button = button("Go", gui.go_button_action)
        stop_button = button("Stop", gui.stop_button_action)
        reset_button = button("Reset", gui.reset_button_action)
        breakpoint_label = QLabel("")
        breakpoint_label.setFont(qfont(p_gui_speed_controls_font))
        breakpoint_label.setStyleSheet("color: %s;" % css_color(K.c_red))
        breakpoint_label.setMinimumWidth(220)
        self_watching_warning_label = QLabel("Warning: Self-watching is disabled")
        self_watching_warning_label.setFont(qfont(p_gui_header_font))
        self_watching_warning_label.setStyleSheet("color: %s;" % css_color(K.c_red))
        options_menu = QMenu("Options")
        options_menu.addAction("Set breakpoint", set_breakpoint_action)
        options_menu.addAction("Clear breakpoint", clear_breakpoint_action)
        options_menu.addAction("Step mode interval", set_step_interval_action)
        controls = QHBoxLayout(speed_controls)
        controls.setContentsMargins(6, 3, 6, 3)
        controls.addWidget(slider_frame)
        controls.addSpacing(10)
        for b in (step_button, go_button, stop_button, reset_button):
            controls.addWidget(b)
        layout = QHBoxLayout(strip)
        layout.setContentsMargins(15, 5, 15, 5)
        layout.addWidget(info_label)
        layout.addWidget(command_line)
        layout.addSpacing(15)
        layout.addWidget(speed_controls)
        layout.addSpacing(15)
        layout.addWidget(breakpoint_label)
        layout.addWidget(self_watching_warning_label)
        layout.addStretch(1)
        self_watching_warning_label.setVisible(setup.p_self_watching_enabled is False)
        # port: the slider's initial value sets the speed, as gui.py does
        gui.speed_slider_action(speed_slider, gui.p_initial_speed)
        this.strip = strip
        this.info_label = info_label
        this.info_text = "Please enter a problem:"
        this.command_line = command_line
        this.step_button, this.go_button = step_button, go_button
        this.stop_button, this.reset_button = stop_button, reset_button
        this.breakpoint_label = breakpoint_label
        this.self_watching_warning_label = self_watching_warning_label
        this.speed_slider = speed_slider
        this.options_menu = options_menu
        this.menus = [options_menu]
        this.verbose_mode_p = setup.p_verbose
        this.problem = False
        this._set_command_line_look(p_gui_command_line_font, K.c_black,
                                    K.p_gui_command_line_color, "left")
        command_line.setFocus()
        this.widgets = {
            "frame": strip, "info-label": info_label, "command-line": command_line,
            "speed-slider": speed_slider, "step-button": step_button,
            "go-button": go_button, "stop-button": stop_button, "reset-button": reset_button,
            "breakpoint-label": breakpoint_label,
            "self-watching-warning-label": self_watching_warning_label,
            "options-menu": options_menu}

    def _gui(this, fn):
        """port: fn on the GUI thread (now there; posted from another thread)"""
        this.invoker.post(fn)

    # control panel object:
    @message("object-type")
    def object_type(this, self):
        return "control-panel"

    @message("get-widgets")
    def get_widgets(this, self):
        """port: the widgets, for the main window and tests"""
        return this.widgets

    @message("problem-exists?")
    def problem_exists_p(this, self):
        return exists_p(this.problem)

    @message("get-current-problem")
    def get_current_problem(this, self):
        return this.problem

    @message("get-command-line-string")
    def get_command_line_string(this, self):
        return this.invoker.call(this.command_line.text)

    @message("update-current-problem")
    def update_current_problem(this, self, tokens):
        if all(isinstance(t, str) for t in tokens):   # (andmap symbol? tokens)
            utilities.randomize()
        if len(tokens) == 5:
            this.problem = list(tokens)
        elif len(tokens) == 3:
            this.problem = [*tokens, False, chez.random_seed()]
        elif isinstance(tokens[3], str):
            this.problem = [*tokens, chez.random_seed()]
        elif isinstance(tokens[3], int):
            this.problem = [tokens[0], tokens[1], tokens[2], False, tokens[3]]
        problem = this.problem
        setup.p_justify_mode = exists_p(problem[3])
        tell(self, "display", chez.format_(
            " ~a -> ~a; ~a -> ~a       seed:  ~a ", problem[0], problem[1], problem[2],
            problem[3] if setup.p_justify_mode else "?", problem[4]))
        this._gui(this.command_line.clear)

    @message("init-new-problem")
    def init_new_problem(this, self, tokens, step_mode_p):
        tell(self, "update-current-problem", tokens)
        tell(self, "switch-to-input-mode")
        problem = this.problem

        def thunk():
            run.init_mcat(*problem)
            if step_mode_p:
                run.step_mode_on()
            run.quiet_break()
            run.run_mcat()
        gui.thread_break(setup.g_repl_thread, False, thunk)

    @message("run-new-problem")
    def run_new_problem(this, self, tokens):
        tell(self, "update-current-problem", tokens)
        tell(self, "switch-to-run-mode")
        problem = this.problem

        def thunk():
            run.init_mcat(*problem)
            run.run_mcat()
        gui.thread_break(setup.g_repl_thread, False, thunk)

    @message("run-demo")
    def run_demo(this, self, problem):
        """port: gui.ss's demo-menu-item action (item 06 highlights the item)"""
        return tell(self, "init-new-problem", problem, False)

    @message("resume-current-problem")
    def resume_current_problem(this, self):
        from metacat import view_globals
        if not exists_p(this.problem):
            return tell(self, "display-error", "No current problem!")
        if run.g_display_mode_p:
            view_globals.restore_current_state()
        gui.thread_break(setup.g_repl_thread, False, run.go)

    @message("reset-current-problem")
    def reset_current_problem(this, self):
        if not exists_p(this.problem):
            return tell(self, "display-error", "No current problem!")
        problem = this.problem

        def thunk():
            run.init_mcat(*problem)
            run.quiet_break()
            run.run_mcat()
        gui.thread_break(setup.g_repl_thread, False, thunk)

    @message("verbose-mode?")
    def verbose_mode_p(this, self):
        return this.verbose_mode_p

    @message("toggle-verbose-mode")
    def toggle_verbose_mode(this, self):
        this.verbose_mode_p = not this.verbose_mode_p
        setup.p_verbose = this.verbose_mode_p

    @message("set-verbose-step-mode")
    def set_verbose_step_mode(this, self, value):
        setup.p_verbose = value or this.verbose_mode_p
        return "done"

    def _set_command_line_look(this, font, fg, bg, justify):
        # a disabled line keeps these colours, as gui.py's Tk entry does
        this.command_line.setFont(qfont(font))
        this.command_line.setStyleSheet("QLineEdit { color: %s; background: %s; }"
                                        % (css_color(fg), css_color(bg)))
        this.command_line.setAlignment(Qt.AlignHCenter if justify == "center" else Qt.AlignLeft)

    def _enable_all(this, command_line, step, go, stop, reset, menus):
        this.command_line.setEnabled(command_line)
        this.step_button.setEnabled(step)
        this.go_button.setEnabled(go)
        this.stop_button.setEnabled(stop)
        this.reset_button.setEnabled(reset)
        for menu in this.menus:
            menu.setEnabled(menus)
            menu.menuAction().setEnabled(menus)

    @message("switch-to-run-mode")
    def switch_to_run_mode(this, self):
        def body():
            this.command_line_action = gui.nop_event_handler
            this._set_command_line_look(p_gui_run_mode_font, K.c_green, K.c_black, "center")
            this.command_line.setText("running...")
            this._enable_all(False, False, False, True, False, False)
        this._gui(body)

    @message("switch-to-input-mode")
    def switch_to_input_mode(this, self):
        def body():
            this.command_line_action = gui.go_button_action
            this.command_line.clear()
            this._set_command_line_look(p_gui_command_line_font, K.c_black,
                                        K.p_gui_command_line_color, "left")
            this._enable_all(True, True, True, False, True, True)
            this.command_line.setFocus()
            # port: the engine parked: every pane shows its final picture now
            if this.parked_hook is not None:
                this.parked_hook()
        this._gui(body)

    @message("switch-to-disabled-mode")
    def switch_to_disabled_mode(this, self):
        def body():
            this.command_line_action = gui.nop_event_handler
            this._enable_all(False, False, False, False, False, False)
        this._gui(body)

    @message("ready-to-edit?")
    def ready_to_edit_p(this, self, theme_type):
        return False      # item 06: the theme edit dialog

    @message("display-breakpoint-message")
    def display_breakpoint_message(this, self):
        text = chez.format_("Breakpoint set for time step ~a", run.g_break_time)
        this._gui(lambda: this.breakpoint_label.setText(text))

    @message("clear-breakpoint-message")
    def clear_breakpoint_message(this, self):
        this._gui(lambda: this.breakpoint_label.setText(""))

    @message("display")
    def display(this, self, message_):
        def body():
            this.info_text = message_
            this.info_label.setText(message_)
        this._gui(body)

    @message("display-error")
    def display_error(this, self, message_):
        def body():
            current_message = this.info_label.text()
            this.info_label.setStyleSheet("color: %s;" % css_color(K.c_red))
            this.info_label.setText(message_)

            def back():   # port: (pause 700) in the GUI thread becomes a timer
                this.info_label.setStyleSheet("color: %s;" % css_color(K.c_black))
                this.info_label.setText(current_message)
            QTimer.singleShot(700, back)
        this._gui(body)

    @message("engine-error")
    def engine_error(this, self, message_):
        """port: an error in the model, which ended the engine thread's thunk (in the
        original it went to the REPL, leaving the control panel in run mode)"""
        tell(self, "switch-to-input-mode")
        tell(self, "display", chez.format_("Error: ~a", message_))

    def otherwise(this, self, msg, args):
        return delegate(self, msg, args, base_object)
