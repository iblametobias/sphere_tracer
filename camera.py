from glm import vec3, mat3
from glm import cross, normalize
from glm import sin, cos, radians
from glm import clamp

class Camera:
    def __init__(self, app, position: vec3, fov: float, yaw: float, pitch: float):
        self.app = app

        self.yaw = radians(yaw)
        self.pitch = radians(pitch)

        self.MAX_PITCH = radians(90)

        self.forward = vec3(0, 0, 1)
        self.right = vec3(1, 0, 0)
        self.position = vec3(position)

        self.fov = fov

        self.movement_speed = 5
        self.sensitivity = 0.1

        self.allow_sprint = True
        self.sprint_speed_multiplier = 5

        self.moved = False

        self.update()

    def update(self):
        self.pitch = clamp(self.pitch, -self.MAX_PITCH, self.MAX_PITCH)

        self.forward.x = cos(self.yaw) * cos(self.pitch)
        self.forward.y = sin(self.pitch)
        self.forward.z = sin(self.yaw) * cos(self.pitch)

        self.forward = normalize(self.forward)
        self.right = normalize(cross(self.forward, vec3(0, 1, 0)))
        self.up = normalize(cross(self.right, self.forward))

        self.m_rotation = mat3(self.right, self.up, self.forward)

    def rotate(self, yaw: float, pitch: float):
        self.yaw += radians(yaw)
        self.pitch += radians(pitch)

    def move_forward(self, direction: vec3 = vec3(0)):
        d_pos = self.m_rotation * direction
        self.position += d_pos * self.movement_speed * self.app.delta_time