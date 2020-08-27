# Ciholas, Inc. - www.ciholas.com 
# Licensed under: creativecommons.org/licenses/by/4.0


class Zone:
    """A zone in the form of a polygon"""
    def __init__(self, name, vertices, color):
        self.name = name
        self.vertices = vertices
        self.color = color
        x_list = []
        y_list = []
        for vertex in self.vertices:
            x_list.append(vertex[0])
            y_list.append(vertex[1])
        # Needs to be stored for future tests
        self.y_list = y_list
        # Finding these extrema helps with calculating where a point is in respect to the zone
        self.x_max = max(x_list)
        self.x_min = min(x_list)
        self.y_max = max(y_list)
        self.y_min = min(y_list)
        # It is easier to calculate position based off each side, so we will now store every line
        side_num = 0
        sides = []
        for vertex in self.vertices:
            side_num += 1
            try:
                sides.append(Line(vertex, self.vertices[side_num]))
            except Exception:
                sides.append(Line(vertex, self.vertices[0]))
        self.sides = sides

    def __str__(self):
        return self.name

    def is_inside(self, point_ray):
        """Determines if the given point, which has been transformed into a ray, is inside or outside
        of the zone.
        """
        x = point_ray.x1
        y = point_ray.y1
        if (x > self.x_max or x < self.x_min or y > self.y_max or y < self.y_min):
            return False
        else:
            # Since the last method didn't work, it is time for the resource expensive test
            # The ray will be compared to every line. If there is an intersection, it will be tracked
            # If there is an odd number of intersections, the point is inside the zone
            # If there is an even number of intersections, the point is outside the zone
            # If the ray is tangent, it will be counted as two intersections
            intersections = 0
            for side in self.sides:
                if point_ray.is_intersected(side):
                    intersections += 1
            # If a line went through a vertex, it counted as two intersections. This will fix that.
            # If a line hit a vertex as a tangent, it had to of been at the the Y max or Y min.
            # We want these counted as 2 intersections, but other vertex intersections should be just 1
            if y in self.y_list and y != self.y_max and y != self.y_min:
                for vertex in self.vertices:
                    if vertex[1] != self.y_max and vertex[1] != self.y_min and vertex[1] == y and vertex[0] > x:
                        intersections -= 1
            if intersections % 2 == 1:
                return True
            else:
                return False


class Line:
    """Holds the data for a line in the form of two points"""
    def __init__(self, point_1, point_2):
        self.x1 = point_1[0]
        self.y1 = point_1[1]
        self.x2 = point_2[0]
        self.y2 = point_2[1]
        # a, b, c are used with determining interception.
        #     It is more efficient to calculate them once in the construction
        #     than it is to calculate them every time they are used.
        self.intercept_coeff_a = self.y2 - self.y1
        self.intercept_coeff_b = self.x1 - self.x2
        self.intercept_coeff_c = (self.x2 * self.y1) - (self.x1 * self.y2)

    def is_intersected(self, line):
        """Determines if this line intersects the given line."""
        d1 = (self.intercept_coeff_a * line.x1) + (self.intercept_coeff_b * line.y1) + self.intercept_coeff_c
        d2 = (self.intercept_coeff_a * line.x2) + (self.intercept_coeff_b * line.y2) + self.intercept_coeff_c
        if (d1 > 0 and d2 > 0) or (d1 < 0 and d2 < 0):
            return False

        d1 = (line.intercept_coeff_a * self.x1) + (line.intercept_coeff_b * self.y1) + line.intercept_coeff_c
        d2 = (line.intercept_coeff_a * self.x2) + (line.intercept_coeff_b * self.y2) + line.intercept_coeff_c
        if (d1 > 0 and d2 > 0) or (d1 < 0 and d2 < 0):
            return False

        # If both of the above checks pass, the two lines could still be collinear.
        if (abs((self.intercept_coeff_a * line.intercept_coeff_b) - (line.intercept_coeff_a * self.intercept_coeff_b)) < .00001):
            return False

        return True