#!usr/bin/env

"""
Version 0.1
Made by 0rd3r
"""

import pygame as pg
from pygame.locals import *

import moderngl as gl

import numpy as np

from pyglm import glm
from pyglm.glm import vec2, vec3

from sys import exit

from dataclasses import is_dataclass

from camera import Camera
from dclasses import Sphere
import world1

class App(object):
    def __init__(self):
        self.screen = pg.display.set_mode((1600, 900), OPENGL | DOUBLEBUF | RESIZABLE)
        self.resolution = vec2(pg.display.get_window_size())
        self.resolution_tuple = tuple(glm.ivec2(self.resolution))

        # pg.mouse.set_visible(False)
        # pg.event.set_grab(True)

        self.ctx = gl.create_context(require=4_6_0)


        self.clock = pg.time.Clock()
        self.delta_time = 0.0
        self.running_time = 0.0

        self.camera = Camera(self, vec3(7, 7, 7), 60, 225, -30)

        self.rays_per_pixel: int = 4
        self.max_bounce_limit: int = 8

        self.shader_files = {}
        for file in ("raytrace.glsl", "quad.glsl"):
            f = open("shaders\\" + file, 'r')
            self.shader_files[file.removesuffix(".glsl")] = f.read()
            f.close()

        self.program = self.ctx.program(
            vertex_shader=self.shader_files["quad"],
            fragment_shader=self.shader_files["raytrace"]
        )

        self.update_accumulation_fbo()

        self.program["resolution"].write(self.resolution)
        self.program["fov"] = self.camera.fov
        self.program["skyboxLightStrength"].value = .35
        self.program["raysPerPixel"].value = self.rays_per_pixel
        self.program["maxBounceLimit"].value = self.max_bounce_limit

        self.spheres: list[Sphere] = world1.spheres
        self.program["sphereAmount"].value = len(self.spheres)
        for i, sphere in enumerate(self.spheres):
            self.load_dataclass_to_uniform(sphere, f"spheres[{i}]")

        self.vao = self.ctx.vertex_array(self.program, [])

    def load_dataclass_to_uniform(self, dclass, uniform_name: str):
        for key, value in dclass.__dict__.items():
            addr = ".".join((uniform_name, key))
            if is_dataclass(value):
                self.load_dataclass_to_uniform(value, addr)
            else:
                self.program[addr].value = value
    
    def update_sphere(self, index: int):
        self.load_dataclass_to_uniform(self.spheres[index], f"spheres[{index}]")

    def update_accumulation_fbo(self):
        self.continue_frame_accumulaion = True
        self.accumulation_frame = 0
        self.frame_render_time = 0.0

        self.previous_frame_texture = self.ctx.texture(self.resolution_tuple, 4)
        self.previous_frame = self.ctx.framebuffer(self.previous_frame_texture)

    def update(self):
        self.camera.update()

        self.continue_frame_accumulaion = self.continue_frame_accumulaion and not self.camera.moved

        self.accumulation_frame *= self.continue_frame_accumulaion
        self.frame_render_time *= self.continue_frame_accumulaion

        self.accumulation_frame += 1
        self.frame_render_time += self.delta_time


        self.max_bounce_limit = glm.clamp(self.max_bounce_limit, 0, 16)

        self.update_uniforms()

        self.vao.render(vertices=6)

        self.ctx.copy_framebuffer(self.previous_frame, self.ctx.screen)
        self.ctx.copy_framebuffer(self.previous_frame_texture, self.previous_frame)

        self.continue_frame_accumulaion = True

    def update_uniforms(self):
        self.program["resolution"].write(self.resolution)
        self.program["fov"] = self.camera.fov
        
        self.program["forward"].write(self.camera.forward)
        self.program["right"].write(self.camera.right)
        self.program["up"].write(self.camera.up)
        self.program["position"].write(self.camera.position)
        
        self.previous_frame_texture.use(location=0)
        self.program["prev"] = 0
        self.program["accumulationFrame"].value = self.accumulation_frame

        self.program["raysPerPixel"].value = self.rays_per_pixel
        self.program["maxBounceLimit"].value = self.max_bounce_limit


    def handle_events(self):
        for event in pg.event.get():
            if event.type == QUIT:
                self.stop()
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    self.stop()
                if event.key == K_UP:
                    self.max_bounce_limit += 1
                    self.continue_frame_accumulaion = False
                if event.key == K_DOWN:
                    self.max_bounce_limit -= 1
                    self.continue_frame_accumulaion = False
            if event.type == VIDEORESIZE:
                w, h = event.size
                pg.display.set_mode((w, h), DOUBLEBUF | OPENGL | RESIZABLE)
                self.resolution_tuple = (w, h)
                self.resolution = vec2(w, h)
                self.update_accumulation_fbo()
                self.ctx.viewport = (0, 0, w, h)

    def debug(self):
        ... # This is where you would implement your debug functionality


    def run(self, debug=False):
        while True:
            self.delta_time = self.clock.tick() / 1000.0 # Clock.tick() returns miliseconds
            self.running_time += self.delta_time
            self.fps_est = self.clock.get_fps()

            self.keys = pg.key.get_pressed()
            self.mouse_rel = pg.mouse.get_rel()
            self.mouse_inputs = pg.mouse.get_pressed()

            self.handle_events()
            
            pg.display.set_caption(
                f"Fps: {self.fps_est:.1f}  Current frame render time: {self.frame_render_time:.2f}s"
            )

            if debug: self.debug()

            self.update()

            pg.display.flip()
            self.ctx.clear(0, 0, 0)


    def stop(self):
        exit()


if __name__ == "__main__":
    app = App()
    app.run(debug=True)