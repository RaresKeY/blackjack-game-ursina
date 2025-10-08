from ursina import *  # type: ignore
from panda3d.core import Quat

import numpy as np
class LTable:
    def __init__(self, step=0.1):
        import math
        self.step = step
        self.mult = 1.0 / step
        self.size = int(round(360 * self.mult))

        # sin table
        self.sin_table = [math.sin(math.radians(i * step)) for i in range(self.size)]

        # arcsin table
        self.x_values = [i * step - 1 for i in range(int(2 / step) + 1)]
        self.asin_table = [math.degrees(math.asin(x)) for x in self.x_values]

    def sin_lut(self, deg):
        idx = int((deg * self.mult) % self.size)
        return self.sin_table[idx]

    def cos_lut(self, deg):
        return self.sin_lut(deg + 90)
    
    def tan_lut(self, deg):
        cos_val = self.cos_lut(deg)
        if abs(cos_val) < 1e-9:  # avoid division by zero
            raise ZeroDivisionError(f"tan undefined for {deg}° (cos≈0)")
        return self.sin_lut(deg) / cos_val
    
    def acos_lut(self, x):
        return 90.0 - self.asin_lut(x)

    def asin_lut(self, x):
        if x < -1 or x > 1:
            raise ValueError("asin domain is [-1, 1]")

        # scale input to index
        idx = (x + 1) / self.step
        i = int(idx)

        if i >= len(self.x_values) - 1:
            return self.asin_table[-1]

        # interpolation
        x0, y0 = self.x_values[i], self.asin_table[i]
        x1, y1 = self.x_values[i + 1], self.asin_table[i + 1]

        t = (x - x0) / (x1 - x0)
        return y0 + t * (y1 - y0)

    def rotate_q(self, start_quaternion, angle_deg, axis):
        """Rotate around start_quaternion by angle_deg along axis"""
        rad = angle_deg
        a = self.cos_lut(rad / 2)
        b = self.sin_lut(rad / 2)

        if axis == 'x':
            step = Quat(a, b, 0, 0)
        elif axis == 'y':
            step = Quat(a, 0, b, 0)
        elif axis == 'z':
            step = Quat(a, 0, 0, b)
        else:
            return None

        # return final quaternion
        return step * start_quaternion

    def normalize(self, v):
        return v / np.linalg.norm(v)

    def slerp(self, q1, q2, t):
        q1, q2 = self.normalize(q1), self.normalize(q2)
        dot = np.dot(q1, q2)

        # handle opposite hemisphere
        if dot < 0.0:
            q2 = -q2
            dot = -dot

        if dot > 0.9995:  # almost linear
            return self.normalize(q1 + t * (q2 - q1))

        # get angle between q1 and q2 in degrees
        theta_0_deg = self.acos_lut(dot)
        theta_deg = theta_0_deg * t

        # orthogonal component
        q3 = self.normalize(q2 - q1 * dot)

        # use LUTs for sin/cos (degrees)
        return q1 * self.cos_lut(theta_deg) + q3 * self.sin_lut(theta_deg)