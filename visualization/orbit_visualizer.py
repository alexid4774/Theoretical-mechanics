import os
os.environ.setdefault('QT_API', 'pyside6')

import math
import sys

import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QWidget, QHBoxLayout, QVBoxLayout, QFormLayout,
    QLabel, QSlider, QDoubleSpinBox, QPushButton, QGroupBox, QMessageBox)
from tudatpy.astro import element_conversion

EARTH_MU = 398600.4418 * 1e9
EARTH_RADIUS = 6371.0


class OrbitVisualizer(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Интерактивная визуализация орбиты')
        self.resize(1180, 740)

        layout = QHBoxLayout(self)
        self.plotter = QtInteractor(self)
        self.plotter.set_background('#0c1425')
        layout.addWidget(self.plotter.interactor, 3)

        controls = QVBoxLayout()
        layout.addLayout(controls, 1)
        controls.addWidget(QLabel('Кеплеровы элементы орбиты'))

        group = QGroupBox('Изменение параметров')
        form = QFormLayout(group)
        controls.addWidget(group)
        self.sliders = {}
        self.spins = {}

        specs = [('a', 'Большая полуось, км', 7000, 6800, 30000, 10, 0),
            ('e', 'Эксцентриситет', 0.05, 0.0, 1.00, 0.01, 2),
            ('i', 'Наклонение, °', 30, 0, 180, 1, 0),
            ('omega', 'Аргумент перицентра, °', 45, 0, 360, 1, 0),
            ('raan', 'Долгота восх. узла, °', 60, 0, 360, 1, 0),
            ('nu', 'Истинная аномалия, °', 90, 0, 360, 1, 0)]
        
        for key, label, default, low, high, step, decimals in specs:
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setMinimum(round(low / step))
            slider.setMaximum(round(high / step))
            slider.setValue(round(default / step))
            spin = QDoubleSpinBox()
            spin.setRange(low, high)
            spin.setSingleStep(step)
            spin.setDecimals(decimals)
            spin.setValue(default)
            slider.valueChanged.connect(lambda n, s=spin, scale=step: s.setValue(n * scale))
            spin.valueChanged.connect(lambda n, s=slider, scale=step: s.setValue(round(n / scale)))
            spin.valueChanged.connect(self.update_orbit)
            row = QVBoxLayout()
            row.addWidget(spin)
            row.addWidget(slider)
            form.addRow(label, row)
            self.sliders[key] = slider
            self.spins[key] = spin

        self.status = QLabel()
        self.status.setWordWrap(True)
        controls.addWidget(self.status)
        reset = QPushButton('Вернуть начальные значения')
        reset.clicked.connect(self.reset_values)
        controls.addWidget(reset)
        controls.addStretch()

        earth = pv.Sphere(radius = EARTH_RADIUS, theta_resolution = 48, phi_resolution = 48)
        self.plotter.add_mesh(earth, color = '#2768ad', smooth_shading = True, name = 'earth')
        self.plotter.add_axes()
        self.update_orbit()
        self.plotter.view_isometric()
        self.plotter.reset_camera()

    def elements(self, nu=None):
        p = self.spins
        return np.array([p['a'].value() * 1000,
            p['e'].value(),
            math.radians(p['i'].value()),
            math.radians(p['omega'].value()),
            math.radians(p['raan'].value()),
            math.radians(p['nu'].value() if nu is None else nu),], dtype=float)

    def update_orbit(self, *args):

        try:
            points = []
            for angle in np.linspace(0, 360, 181):
                state = element_conversion.keplerian_to_cartesian(self.elements(nu=angle), EARTH_MU)
                points.append(state[:3] / 1000)

            points = np.array(points)
            self.plotter.add_mesh(pv.lines_from_points(points, close = False), color = '#54d9f0', line_width = 4, name = 'orbit')

            satellite_state = element_conversion.keplerian_to_cartesian(self.elements(), EARTH_MU)
            satellite_km = satellite_state[:3] / 1000
            satellite = pv.Sphere(radius = 250, center = satellite_km)
            self.plotter.add_mesh(satellite, color = '#ffc35a', name = 'satellite')

            a = self.spins['a'].value()
            e = self.spins['e'].value()
            rp, ra = a * (1 - e), a * (1 + e)
            note = '\nВнимание: орбита проходит внутри Земли.' if rp < EARTH_RADIUS else ''
            self.status.setText(f'Перицентр: {rp:.1f} км от центра Земли\n'f'Апоцентр: {ra:.1f} км от центра Земли'f'{note}')
            self.plotter.render()

        except Exception as exc:
            QMessageBox.critical(self, 'Ошибка вычисления!', str(exc))

    def reset_values(self):
        defaults = {'a': 7000, 'e': 0.05, 'i': 30,'omega': 45, 'raan': 60, 'nu': 90}
        for key, value in defaults.items():
            self.spins[key].setValue(value)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = OrbitVisualizer()
    window.show()
    sys.exit(app.exec())
