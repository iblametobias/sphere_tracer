from pyglm.glm import vec3, cross, normalize, length
from pyglm.glm import sin, cos, radians
from pyglm.glm import clamp

from pygame.locals import *
from pygame import key, mouse

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
        self.sensitivity = 0.005

        self.moved = False

    def update(self):
        self.pitch = clamp(self.pitch, -self.MAX_PITCH, self.MAX_PITCH)

        self.forward.x = cos(self.yaw) * cos(self.pitch)
        self.forward.y = sin(self.pitch)
        self.forward.z = sin(self.yaw) * cos(self.pitch)

        self.forward = normalize(self.forward)
        self.right = normalize(cross(self.forward, vec3(0, 1, 0)))
        self.up = normalize(cross(self.right, self.forward))

        self.update_movement()

    def update_movement(self):
        rotation_speed = self.sensitivity * self.app.mouse_inputs[0]
        self.yaw += self.app.mouse_rel[0] * rotation_speed 
        self.pitch -= self.app.mouse_rel[1] * rotation_speed
        self.moved = any(self.app.mouse_rel) and self.app.mouse_inputs[0]

        keys = self.app.keys
        direction = vec3(0)

        if keys[K_w]:
            direction += self.forward
        if keys[K_s]:
            direction -= self.forward
        if keys[K_a]:
            direction -= self.right
        if keys[K_d]:
            direction += self.right

        if length(direction) < 1e-8:
            return
        
        self.moved = True
        
        direction = normalize(direction)

        move = self.movement_speed * self.app.delta_time * direction
        if keys[K_LSHIFT]:
            move *= 10

        self.position += move