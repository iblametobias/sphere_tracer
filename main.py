import moderngl_window as mglw
from moderngl_window.integrations.imgui import ModernglWindowRenderer
import imgui

from glm import normalize, length
from glm import vec2, vec3

from dataclasses import is_dataclass
from pathlib import Path

from camera import Camera
from ui import UI
from dclasses import Sphere
import world1


class App(mglw.WindowConfig):
    gl_version = (4, 6)
    window_size = (1600, 900)
    aspect_ratio = None
    resizable = True
    resource_dir = Path(__file__).parent

    def __init__(self, **kwargs):
        # Initialize ModernGL Window and ImGui
        super().__init__(**kwargs)
        imgui.create_context()
        self.wnd.ctx.error

        # Compile shaders
        self.program = self.load_program(
            vertex_shader="shaders/quad.glsl", 
            fragment_shader="shaders/raytrace.glsl"
        )
        # Vertex Array Object for the fullscreen quad displaying the raytraced render
        self.vao = self.ctx.vertex_array(self.program, [])

        # Initialize camera and UI objects
        self.ui = UI(self)
        self.ui_renderer = ModernglWindowRenderer(self.wnd)
        self.camera = Camera(self, vec3(7, 7, 7), 60, 225, -40)
        
        # Constants
        self.SIDEBAR_WIDTH = 270 # its just one constant ;-;

        # CPU-side variables
        self.render_resolution = vec2(self.window_size)
        self.rays_per_pixel = 4
        self.max_bounce_limit = 8

        self.allow_accumulation = True
        self.accumulation_frame = 0 
        self.accumulation_time = 0.0 

        self.spheres: list[Sphere] = world1.spheres.copy()
        for i, sphere in enumerate(self.spheres):
            self.load_dataclass_to_uniform(sphere, f"spheres[{i}]")

        # Framebuffers for temporal accumulation
        self.fbo = self.ctx.framebuffer(
            color_attachments=self.ctx.texture(self.window_size, 4)
        )
        self.fbo_prev = self.ctx.framebuffer(
            color_attachments=self.ctx.texture(self.window_size, 4)
        )

        self.ui_renderer.register_texture(self.fbo.color_attachments[0])
        self.ui_renderer.register_texture(self.fbo_prev.color_attachments[0])

        # Initialize uniforms
        self.program["skyboxLightStrength"].value = .67
        self.update_uniforms()


    def update_uniforms(self):
        """Updates all uniforms except for spheres."""

        self.program["resolution"].write(self.render_resolution)
        self.program["fov"] = self.camera.fov

        self.program["forward"].write(self.camera.forward)
        self.program["right"].write(self.camera.right)
        self.program["up"].write(self.camera.up)
        self.program["position"].write(self.camera.position)

        self.program["raysPerPixel"].value = self.rays_per_pixel
        self.program["maxBounceLimit"].value = self.max_bounce_limit

        self.fbo_prev.color_attachments[0].use(location=0)
        self.program["prev"].value = 0
        self.program["accumulationFrame"].value = self.accumulation_frame

        self.program["sphereAmount"].value = len(self.spheres)

    def on_render(self, time: float, frametime: float):
        self.delta_time = frametime

        # Prepare the framebuffer for rendering
        self.fbo.use()
        self.fbo.clear()

        # Update the CPU side
        self.update_camera_movement()
        self.camera.update()
        self.update_accumulation()

        # Update the GPU side
        self.update_uniforms()

        # Render the scene
        self.vao.render(vertices=6)

        # Swap FBOs for next frame
        self.fbo, self.fbo_prev = self.fbo_prev, self.fbo

        # Render the UI to the default framebuffer
        self.wnd.use()
        self.ui.generate_frame()
        self.ui_renderer.render(imgui.get_draw_data())

    def update_accumulation(self):
        if not self.allow_accumulation:
            return
        self.accumulation_frame += 1
        self.accumulation_time += self.delta_time
        
    def reset_accumulation(self):
        self.accumulation_frame = 0
        self.accumulation_time = 0.0

    def update_camera_movement(self):
        move = vec3(0)
        if self.wnd.is_key_pressed(self.wnd.keys.W):
            move += vec3(0, 0, 1)
        if self.wnd.is_key_pressed(self.wnd.keys.S):
            move += vec3(0, 0, -1)
        if self.wnd.is_key_pressed(self.wnd.keys.A):
            move += vec3(-1, 0, 0)
        if self.wnd.is_key_pressed(self.wnd.keys.D):
            move += vec3(1, 0, 0)
        if length(move) < 1e-6:
            return 
        self.reset_accumulation()
        move = normalize(move)
        if self.wnd.is_key_pressed(self.wnd.keys.LEFT_SHIFT):
            move *= self.camera.sprint_speed_multiplier if self.camera.allow_sprint else 1
        self.camera.move_forward(move)


    def load_dataclass_to_uniform(self, dclass, uniform_name: str):
        for key, value in dclass.__dict__.items():
            addr = ".".join((uniform_name, key))
            if is_dataclass(value):
                self.load_dataclass_to_uniform(value, addr)
            else:
                # print(f"Setting uniform {addr} to {value}")
                self.program[addr].value = value

    def on_resize(self, width: int, height: int):
        self.window_size = width, height
        self.render_resolution = vec2(self.window_size)

        self.fbo = self.ctx.framebuffer(
            color_attachments=self.ctx.texture(self.window_size, 4)
        )
        self.fbo_prev = self.ctx.framebuffer(
            color_attachments=self.ctx.texture(self.window_size, 4)
        )
        self.ui_renderer.register_texture(self.fbo.color_attachments[0])
        self.ui_renderer.register_texture(self.fbo_prev.color_attachments[0])
        self.ui_renderer.resize(width, height)

        self.reset_accumulation()

    def on_key_event(self, key, action, modifiers):
        self.ui_renderer.key_event(key, action, modifiers)

    def on_mouse_position_event(self, x, y, dx, dy):
        self.ui_renderer.mouse_position_event(x, y, dx, dy)

    def on_mouse_drag_event(self, x, y, dx, dy):
        if not imgui.get_io().want_capture_mouse:
            if dx or dy: self.reset_accumulation()
            self.camera.rotate(dx * self.camera.sensitivity, -dy * self.camera.sensitivity)
        self.ui_renderer.mouse_drag_event(x, y, dx, dy)

    def on_mouse_scroll_event(self, x_offset, y_offset):
        self.ui_renderer.mouse_scroll_event(x_offset, y_offset)

    def on_mouse_press_event(self, x, y, button):
        self.ui_renderer.mouse_press_event(x, y, button)

    def on_mouse_release_event(self, x: int, y: int, button: int):
        self.ui_renderer.mouse_release_event(x, y, button)

    def on_unicode_char_entered(self, char):
        self.ui_renderer.unicode_char_entered(char)
      

if __name__ == "__main__":
    App.run()