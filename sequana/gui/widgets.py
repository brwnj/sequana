from PyQt5 import QtCore, QtGui
from PyQt5 import QtWidgets as QW
from PyQt5.QtCore import Qt

from sequana.gui.file_browser import FileBrowser


__all__ = ["Ruleform", "GeneralOption", "BooleanOption",
"TextOption", "NumberOption", "FileBrowserOption"]


class Ruleform(QW.QGroupBox):
    do_option = "do"
    def __init__(self, rule_name, rule_dict, count=0, browser_keywords=[],
                 generic=False):
        super().__init__(rule_name)

        # to handle recursive case
        self.do_widget = None

        self.rule_name = rule_name
        self.rule_dict = rule_dict
        self.layout = QW.QVBoxLayout(self)
        self.layout.setSpacing(2)
        self.setAutoFillBackground(True)

        rules = list(self.rule_dict.keys())
        rules.sort()
        if "do" in rules:
            rules.remove("do")
            rules.insert(0, "do")

        for rule in rules:
            option = rule
            value = self.rule_dict[rule]

            if option.endswith("_directory"):
                option_widget = FileBrowserOption(option, value,
                                                  directory=True)
            elif option.endswith("_file"):
                option_widget = FileBrowserOption(option, value,
                                                  directory=False)
            elif option in browser_keywords:
                option_widget = FileBrowserOption(option, value,
                                                  directory=False)
            elif isinstance(value, bool) or option == "do":
                # for the do option, we need to check its value
                option_widget = BooleanOption(option, value)
                if option == Ruleform.do_option:
                    self.do_widget = option_widget
                    option_widget.connect(self._widget_lock)
            elif generic is True:
                value = str(value)
                option_widget = TextOption(option, value)
            else:
                try:
                    option_widget = NumberOption(option, value)
                except TypeError:
                    try:
                        option_widget = TextOption(option, value)
                    except TypeError:
                        option_widget = Ruleform(option, value)
            self.layout.addWidget(option_widget)
        try:
            self._widget_lock(self.do_widget.get_value())
        except AttributeError:
            pass

    def get_name(self):
        return self.rule_name

    def get_layout(self):
        return self.layout

    def get_do_rule(self):
        """ If there are no "do widget", rules must be done. Else, it gets value
        of check box.
        """
        if self.do_widget is None:
            return True
        else:
            return self.do_widget.get_value()

    def is_option(self):
        return False

    def connect_do(self, task):
        if self.do_widget:
            self.do_widget.connect(task)

    def _widget_lock(self, switch_bool):
        widget_list = (self.layout.itemAt(i).widget() for i in
                       range(self.layout.count()))
        for w in widget_list:
            if w is self.do_widget:
                continue
            w.set_enable(switch_bool)

    def set_enable(self, switch_bool):
        self._widget_lock(switch_bool)


class GeneralOption(QW.QWidget):
    """ Parent class for Options. It defines design of options
    """
    def __init__(self, option):
        super().__init__()
        self.option = option
        self.layout = QW.QHBoxLayout(self)
        self.layout.setContentsMargins(0, 3, 0, 3)
        self.layout.addWidget(QW.QLabel(option))

    def get_name(self):
        return self.option

    def is_option(self):
        return True

    def get_value(self):
        pass

    def get_tuple(self):
        return (self.get_name(), self.get_value())

    def set_enable(self):
        pass


class BooleanOption(GeneralOption):
    """ Wrapp QCheckBox class
    """
    def __init__(self, option, value):
        # Make sure the value is a boolean
        if isinstance(value, str):
            if value.lower() in ['yes', "true", "on"]:
                value = True
            elif value in ['no', "false", "off"]:
                value = False
        super().__init__(option)

        self.check_box = QW.QCheckBox()
        self.check_box.setChecked(value)

        self.answer = QW.QLabel()
        self.switch_answer()

        self.check_box.clicked.connect(self.switch_answer)

        self.layout.addWidget(self.check_box)
        self.layout.addWidget(self.answer)

    def get_value(self):
        return self.check_box.isChecked()

    def set_enable(self, switch_bool):
        self.check_box.setEnabled(switch_bool)

    def switch_answer(self):
        value = self.get_value()
        if value:
            self.answer.setText("<b> yes <\b>")
        else:
            self.answer.setText("<b> no <\b>")

    def connect(self, task):
        self.check_box.clicked.connect(task)


class TextOption(GeneralOption):
    def __init__(self, option, value):
        super().__init__(option)
        self.text = QW.QLineEdit(value)

        self.layout.addWidget(self.text)

    def get_value(self):
        if not self.text.text():
            return "''"
        return self.text.text()

    def set_value(self, text):
        self.text.setText(text)

    def set_enable(self, switch_bool):
        self.text.setEnabled(switch_bool)


class NumberOption(GeneralOption):
    def __init__(self, option, value):
        super().__init__(option)

        if isinstance(value, float):
            self.number = QW.QDoubleSpinBox()
        else:
            self.number = QW.QSpinBox()
        self.number.setRange(-1000000, 1000000)
        self.number.setValue(value)
        self.number.installEventFilter(self)

        self.layout.addWidget(self.number)

    def get_value(self):
        return self.number.value()

    def set_value(self, value):
        self.number.setValue(value)

    def set_range(self, min_value, max_value):
        self.number.setRange(min_value, max_value)

    def set_enable(self, switch_bool):
        self.number.setEnabled(switch_bool)

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.Wheel and source is self.number:
            return True
        return False


class FileBrowserOption(GeneralOption):
    def __init__(self, option, value=None, directory=False):
        super().__init__(option)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.browser = FileBrowser(directory=directory)
        self.layout.addWidget(self.browser)
        if value:
            self.browser.set_filenames(value)

    def get_value(self):
        if not self.browser.get_filenames():
            return "''"
        return self.browser.get_filenames()

    def set_enable(self, switch_bool):
        self.browser.set_enable(switch_bool)

