import math
import sys

import numpy as np
from PySide6.QtWidgets import (QApplication, QComboBox, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget)
from tudatpy.astro import element_conversion

EARTH_MU = 398600.4418


class OrbitConverter(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Конвертер орбитальных элементов')
        self.resize(650, 560)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Преобразование орбитальных элементов'))

        self.mode = QComboBox()
        self.mode.addItems(['Декартовы в Кеплеровы', 'Кеплеровы в Декартовы'])
        self.mode.currentIndexChanged.connect(self.change_mode)
        layout.addWidget(self.mode)

        self.group = QGroupBox('Исходные данные')
        self.form = QFormLayout(self.group)
        self.entries = []
        self.labels = []
        for i in range(6):
            entry = QLineEdit()
            label = QLabel()
            self.entries.append(entry)
            self.labels.append(label)
            self.form.addRow(label, entry)
        layout.addWidget(self.group)

        mu_row = QHBoxLayout()
        mu_row.addWidget(QLabel('Гравитационный параметр mu (км^3/с^2):'))
        self.mu_entry = QLineEdit(str(EARTH_MU))
        mu_row.addWidget(self.mu_entry)
        layout.addLayout(mu_row)

        self.button = QPushButton('Рассчитать')
        self.button.clicked.connect(self.calculate)
        layout.addWidget(self.button)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(QLabel('Результат:'))
        layout.addWidget(self.output)
        self.change_mode()

    def change_mode(self):

        if self.mode.currentIndex() == 0:
            labels = ['x (км)', 'y (км)', 'z (км)',
                      'V_x (км/с)', 'V_y (км/с)', 'V_z (км/с)']
            defaults = ['7000', '0', '0', '0', '7.5', '1.0']
        else:
            labels = ['a (км)', 'e', 'i (°)', 'omega (°)', 'Omega (°)', 'nu (°)']
            defaults = ['7000', '0.01', '30', '45', '60', '90']

        for label, entry, default, widget in zip(labels, self.entries, defaults, self.labels):
            widget.setText(label + ':')
            entry.setText(default)
        self.output.clear()

    def calculate(self):

        try:

            values = []
            for entry in self.entries:
                text = entry.text()
                text = text.replace(',', '.')
                number = float(text)
                values.append(number)
            mu = float(self.mu_entry.text().replace(',', '.'))

            if self.mode.currentIndex() == 0:
                result = self.to_keplerian(values, mu)
            else:
                result = self.to_cartesian(values, mu)
            self.output.setPlainText(result)

        except (ValueError, RuntimeError, OverflowError, FloatingPointError) as error:
            QMessageBox.critical(self, 'Ошибка вычисления!', str(error))

    def to_keplerian(self, values, mu):

        r = np.array(values[:3])
        v = np.array(values[3:])

        if np.linalg.norm(np.cross(r, v)) <= 1e-12 * np.linalg.norm(r) * np.linalg.norm(v):
            raise ValueError('Радиальная траектория!')

        state = np.array(values) * 1000 
        a, e, i, omega, raan, nu = element_conversion.cartesian_to_keplerian(state, mu * 1e9)
        angles = [math.degrees(x) % 360 for x in (i, omega, raan, nu)]
        
        first = 'Фокальный параметр p' if e == 1.0 else 'Большая полуось a'
        result = (f'{first}: {a / 1000:.8f} км\n'
                  f'Эксцентриситет e: {e:.10f}\n'
                  f'Наклонение i: {angles[0]:.8f}°\n'
                  f'Аргумент перицентра omega: {angles[1]:.8f}°\n'
                  f'Долгота восходящего узла Omega: {angles[2]:.8f}°\n'
                  f'Истинная аномалия nu: {angles[3]:.8f}°')

        return result

    def to_cartesian(self, values, mu):
        a, e, i, omega, raan, nu = values
        if e < 0:
            raise ValueError('Эксцентриситет не может быть отрицательным!')
        if not 0 <= i <= 180:
            raise ValueError('Наклонение должно быть от 0° до 180°!')
        if e < 1 and a <= 0:
            raise ValueError('Для эллиптической орбиты a должно быть положительным!')
        if e > 1 and a >= 0:
            raise ValueError('Для гиперболической орбиты a должно быть отрицательным!')
        if e == 1 and a <= 0:
            raise ValueError('Для параболической орбиты в поле a задаётся p > 0!')
        if 1 + e * math.cos(math.radians(nu)) <= 1e-12:
            raise ValueError('Такая истинная аномалия не задаёт конечную точку орбиты!')

        elements = np.array([a * 1000, e, *np.radians([i, omega, raan, nu])])
        state = element_conversion.keplerian_to_cartesian(elements, mu * 1e9) / 1000
        names = ('x', 'y', 'z', 'V_x', 'V_y', 'V_z')
        lines = []

        for name, value in zip(names, state):
            unit = 'км' if name in ('x', 'y', 'z') else 'км/с'
            lines.append(f'{name}: {value:.8f} {unit}')
        return '\n'.join(lines)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = OrbitConverter()
    window.show()
    sys.exit(app.exec())
