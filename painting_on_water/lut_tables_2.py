from ursina import *  # type: ignore
from panda3d.core import Quat
import numpy as np
import math

class LTable:
    def __init__(self, step=0.1, radians=False):
        self.step = step
        self.radians = radians
        self.mult = 1.0 / step
        self.size = int(round((2 * math.pi if radians else 360) * self.mult))

        # sin table
        if radians:
            self.sin_table = [math.sin(i * step) for i in range(self.size)]
        else:
            self.sin_table = [math.sin(math.radians(i * step)) for i in range(self.size)]

        # arcsin table
        if radians:
            self.x_values = [i * step - 1 for i in range(int(2 / step) + 1)]
            self.asin_table = [math.asin(x) for x in self.x_values]
        else:
            self.x_values = [i * step - 1 for i in range(int(2 / step) + 1)]
            self.asin_table = [math.degrees(math.asin(x)) for x in self.x_values]

    def sin_lut(self, angle):
        idx = int((angle * self.mult) % self.size)
        return self.sin_table[idx]

    def cos_lut(self, angle):
        return self.sin_lut(angle + (math.pi/2 if self.radians else 90))

    def tan_lut(self, angle):
        cos_val = self.cos_lut(angle)
        if abs(cos_val) < 1e-9:
            raise ZeroDivisionError(f"tan undefined for {angle}{' rad' if self.radians else '°'}")
        return self.sin_lut(angle) / cos_val

    def acos_lut(self, x):
        if self.radians:
            return (math.pi/2) - self.asin_lut(x)
        else:
            return 90.0 - self.asin_lut(x)

    def asin_lut(self, x):
        if x < -1 or x > 1:
            raise ValueError("asin domain is [-1, 1]")

        idx = (x + 1) / self.step
        i = int(idx)

        if i >= len(self.x_values) - 1:
            return self.asin_table[-1]

        # interpolation
        x0, y0 = self.x_values[i], self.asin_table[i]
        x1, y1 = self.x_values[i + 1], self.asin_table[i + 1]

        t = (x - x0) / (x1 - x0)
        return y0 + t * (y1 - y0)

    def rotate_q(self, start_quaternion, angle, axis):
        """Rotate around start_quaternion by angle (deg or rad depending on mode)"""
        half_angle = angle / 2
        a = self.cos_lut(half_angle)
        b = self.sin_lut(half_angle)

        if axis == 'x':
            step = Quat(a, b, 0, 0)
        elif axis == 'y':
            step = Quat(a, 0, b, 0)
        elif axis == 'z':
            step = Quat(a, 0, 0, b)
        else:
            return None

        return step * start_quaternion

    def normalize(self, v):
        return v / np.linalg.norm(v)

    def slerp(self, q1, q2, t):
        q1, q2 = self.normalize(q1), self.normalize(q2)
        dot = np.dot(q1, q2)

        if dot < 0.0:
            q2 = -q2
            dot = -dot

        if dot > 0.9995:
            return self.normalize(q1 + t * (q2 - q1))

        theta_0 = self.acos_lut(dot)
        theta = theta_0 * t

        q3 = self.normalize(q2 - q1 * dot)

        return q1 * self.cos_lut(theta) + q3 * self.sin_lut(theta)
