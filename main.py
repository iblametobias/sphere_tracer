import glm
from glm import vec2, vec3

import moderngl as gl

import imgui
import moderngl_window as mglw
from moderngl_window.integrations.imgui import ModernglWindowRenderer

from camera import Camera

from dataclasses import is_dataclass

from dclasses import Sphere, Material
import world1

class WindowEvents(mglw.WindowConfig):
    gl_version = (4, 6)
    title = "ModernGL Window"
    window_size = (1600, 900)
    aspect_ratio = None
    resizable = True
    resource_dir = "C:\\Users\\Tobiasz\\Documents\\py\\sphere_tracer\\"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        imgui.create_context()
        self.wnd.ctx.error

        self.imgui = ModernglWindowRenderer(self.wnd)
        self.SIDEBAR_WIDTH = 270

        self.camera = Camera(self, vec3(7, 7, 7), 60, 225, -40)

        self.render_resolution = vec2(self.window_size)
        self.rays_per_pixel = 4
        self.max_bounce_limit = 8

        self.allow_accumulation = True
        self.accumulation_frame = 0 
        self.accumulation_time = 0.0 

        self.program = self.load_program(
            vertex_shader="shaders/quad.glsl", 
            fragment_shader="shaders/raytrace.glsl"
        )

        self.program["resolution"].write(self.render_resolution)
        self.program["fov"] = self.camera.fov
        self.program["skyboxLightStrength"].value = .67
        self.program["raysPerPixel"].value = self.rays_per_pixel
        self.program["maxBounceLimit"].value = self.max_bounce_limit

        self.spheres: list[Sphere] = world1.spheres.copy()
        self.program["sphereAmount"].value = len(self.spheres)
        for i, sphere in enumerate(self.spheres):
            self.load_dataclass_to_uniform(sphere, f"spheres[{i}]")

        # --- FBOs for temporal accumulation ---
        self.fbo = self.ctx.framebuffer(
            color_attachments=self.ctx.texture(self.window_size, 4)
        )
        self.fbo_prev = self.ctx.framebuffer(
            color_attachments=self.ctx.texture(self.window_size, 4)
        )

        self.imgui.register_texture(self.fbo.color_attachments[0])
        self.imgui.register_texture(self.fbo_prev.color_attachments[0])

        self.vao = self.ctx.vertex_array(self.program, [])

    def update_uniforms(self):
        self.program["resolution"].write(self.render_resolution)
        self.program["fov"] = self.camera.fov

        self.program["forward"].write(self.camera.forward)
        self.program["right"].write(self.camera.right)
        self.program["up"].write(self.camera.up)
        self.program["position"].write(self.camera.position)

        self.program["raysPerPixel"].value = self.rays_per_pixel
        self.program["maxBounceLimit"].value = self.max_bounce_limit

        # Temporal accumulation uniforms
        self.program["prev"].value = 0  # Texture unit 0
        self.fbo_prev.color_attachments[0].use(location=0)
        self.program["accumulationFrame"].value = self.accumulation_frame

        self.program["sphereAmount"].value = len(self.spheres)


    def on_render(self, time: float, frametime: float):
        self.delta_time = frametime
        self.running_time = time

        # Bind previous frame texture to shader
        self.program["prev"].value = 0
        self.fbo_prev.color_attachments[0].use(location=0)
        self.program["accumulationFrame"].value = self.accumulation_frame

        self.fbo.use()
        self.fbo.clear()

        self.update_camera_movement()

        self.camera.update()

        self.update_uniforms()

        if self.allow_accumulation:
            self.accumulation_time += self.delta_time
            self.accumulation_time *= bool(self.accumulation_frame) # Reset if no accumulation frames
            self.accumulation_frame += 1
        else:
            self.accumulation_frame = 0
            self.accumulation_time = 0.0

        self.vao.render(vertices=6)

        # Swap FBOs for next frame
        self.fbo, self.fbo_prev = self.fbo_prev, self.fbo

        # Only show the latest result in the UI
        self.wnd.use()
        self.render_ui()

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
        if glm.length(move) < 1e-6:
            return 
        self.accumulation_frame = 0 
        move = glm.normalize(move)
        if self.wnd.is_key_pressed(self.wnd.keys.LEFT_SHIFT):
            move *= self.camera.sprint_speed_multiplier if self.camera.allow_sprint else 1
        self.camera.move_forward(move)


    def render_ui(self):
        imgui.new_frame()

        # 1. Draw the raytraced frame as a background
        imgui.push_style_var(imgui.STYLE_WINDOW_PADDING, (0, 0))
        imgui.set_next_window_position(0, 0)
        imgui.set_next_window_size(*self.window_size)
        imgui.begin(
            "Background",
            False,
            imgui.WINDOW_NO_TITLE_BAR
            | imgui.WINDOW_NO_MOVE
            | imgui.WINDOW_NO_SCROLLBAR
            | imgui.WINDOW_NO_COLLAPSE
            | imgui.WINDOW_NO_SAVED_SETTINGS
            | imgui.WINDOW_NO_INPUTS
            | imgui.WINDOW_NO_BRING_TO_FRONT_ON_FOCUS
            | imgui.WINDOW_NO_BACKGROUND
        )
        imgui.image(self.fbo.color_attachments[0].glo, *self.window_size)
        imgui.end()
        imgui.pop_style_var()

        # --- LEFT SIDEBAR ---
        imgui.set_next_window_position(0, 0)
        imgui.set_next_window_size(self.SIDEBAR_WIDTH, self.window_size[1])
        imgui.begin(
            "##Sidebar",  # No header/title bar
            False,
            imgui.WINDOW_NO_TITLE_BAR | imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_SAVED_SETTINGS | imgui.WINDOW_NO_MOVE
        )

        # Collapsible Raytracer Settings
        if imgui.collapsing_header("Raytracer Settings", flags=imgui.TREE_NODE_DEFAULT_OPEN)[0]:
            imgui.set_next_item_width(160)
            _, self.rays_per_pixel = imgui.slider_int(
                "Rays/Pixel", self.rays_per_pixel, 1, 20
            )
            imgui.set_next_item_width(160)
            _, self.max_bounce_limit = imgui.slider_int(
                "Max Bounces", self.max_bounce_limit, 1, 4
            )
            imgui.text(f"MSPF: {(self.delta_time * 1000):.0f} ms")
            imgui.text(f"Accumulation time: {self.accumulation_time:.2f}s")
            _, self.allow_accumulation = imgui.checkbox(
                "Allow Accumulation", self.allow_accumulation
            )

        # Collapsible World Settings
        if imgui.collapsing_header("World Settings", flags=imgui.TREE_NODE_DEFAULT_OPEN)[0]:
            remove_indices = []
            for i, sphere in enumerate(self.spheres):
                if self.render_sphere_editor(sphere, i):
                    remove_indices.append(i)

            # Remove spheres after iteration to avoid index issues
            for idx in reversed(remove_indices):
                del self.spheres[idx]
                self.accumulation_frame = 0

            if remove_indices:
                self.program["sphereAmount"].value = len(self.spheres)
                for i, sphere in enumerate(self.spheres):
                    self.load_dataclass_to_uniform(sphere, f"spheres[{i}]")

        if imgui.button("Add Sphere"):
            from dclasses import Sphere, Material  # Ensure import at top of file
            self.spheres.append(Sphere(center=vec3(0,0,0), radius=1.0, material=Material()))
            self.accumulation_frame = 0
            self.load_dataclass_to_uniform(self.spheres[-1], f"spheres[{len(self.spheres) - 1}]")

        if imgui.button("Print all"):
            print(self.spheres)

        imgui.end()

        # --- RIGHT SIDEBAR ---
        right_x = self.window_size[0] - self.SIDEBAR_WIDTH
        imgui.set_next_window_position(right_x, 0)
        imgui.set_next_window_size(self.SIDEBAR_WIDTH, self.window_size[1])
        imgui.begin(
            "##CameraSidebar",  # No header/title bar
            False,
            imgui.WINDOW_NO_TITLE_BAR | imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_SAVED_SETTINGS | imgui.WINDOW_NO_MOVE
        )

        # Collapsible Camera Controls
        if imgui.collapsing_header("Camera Controls", flags=imgui.TREE_NODE_DEFAULT_OPEN)[0]:
            imgui.text(
                f"Position: ({self.camera.position.x:6.2f}, {self.camera.position.y:6.2f}, {self.camera.position.z:6.2f})"
            )
            imgui.text(
                f"Forward:  ({self.camera.forward.x:6.2f}, {self.camera.forward.y:6.2f}, {self.camera.forward.z:6.2f})"
            )
            imgui.set_next_item_width(160)
            changed, self.camera.fov = imgui.slider_float(
                "FOV", self.camera.fov, 30.0, 90.0
            )
            if changed:
                self.accumulation_frame = 0
            imgui.set_next_item_width(160)
            _, self.camera.sensitivity = imgui.slider_float(
                "Sensitivity", self.camera.sensitivity, 0.05, 0.4
            )
            imgui.set_next_item_width(100)
            _, self.camera.movement_speed = imgui.drag_float(
                "Movement Speed", self.camera.movement_speed, 0.02, 0.5, 5.0, format="%.2f"
            )
            _, self.camera.allow_sprint = imgui.checkbox(
                "Allow Sprint", self.camera.allow_sprint
            )
            imgui.set_next_item_width(100)
            _, self.camera.sprint_speed_multiplier = imgui.drag_float(
                "Sprint Speed Multiplier", self.camera.sprint_speed_multiplier, 0.05, 2.0, 20.0, format="%.2f"
            )

        imgui.end()
        imgui.render()
        self.imgui.render(imgui.get_draw_data())

    def render_sphere_editor(self, sphere: Sphere, index: int) -> bool:
        if not imgui.tree_node(f"Sphere {index}"):
            return False # No changes if tree node is not expanded
        
        imgui.push_id(str(index))
        # --- Position ---
        imgui.set_next_item_width(160)
        center_changed, *new_center = imgui.drag_float3(
            "Center", *tuple(sphere.center), 0.01, format="%.2f"
        )
        if center_changed:
            sphere.center = vec3(*new_center)
            self.program[f"spheres[{index}].center"].write(sphere.center)
            self.accumulation_frame = 0

        # --- Radius ---
        imgui.set_next_item_width(160)
        radius_changed, sphere.radius = imgui.drag_float(
            f"Radius", sphere.radius, 0.01, 0, 100.0, format="%.2f"
        )
        if radius_changed:
            self.program[f"spheres[{index}].radius"].value = sphere.radius
            self.accumulation_frame = 0

        # --- Material ---
        # Color (RGB sliders)
        imgui.set_next_item_width(160)
        color_changed, *new_color = imgui.color_edit3(
            "Albedo", *tuple(sphere.material.color)
        )
        if color_changed:
            sphere.material.color = vec3(*new_color)
            self.program[f"spheres[{index}].material.color"].write(sphere.material.color)
            self.accumulation_frame = 0
        # Smoothness
        imgui.set_next_item_width(160)
        changed_smooth, sphere.material.smoothness = imgui.slider_float(
            "Smoothness", sphere.material.smoothness, 0.0, 1.0, format="%.2f"
        )
        if changed_smooth:
            self.program[f"spheres[{index}].material.smoothness"].value = (sphere.material.smoothness)
            self.accumulation_frame = 0
        # Emission Color (RGB sliders)
        imgui.set_next_item_width(160)
        emission_changed, *new_emission = imgui.color_edit3(
            "Emission", *tuple(sphere.material.emissionColor)
        )
        if emission_changed:
            sphere.material.emissionColor = vec3(*new_emission)
            self.program[f"spheres[{index}].material.emissionColor"].write(sphere.material.emissionColor)
            self.accumulation_frame = 0
        # Emission Strength
        imgui.set_next_item_width(160)
        changed_em_strength, sphere.material.emissionStrength = imgui.drag_float(
            "Brightness", sphere.material.emissionStrength, 0.01, 0, 5, format="%.2f"
        )
        if changed_em_strength:
            self.program[f"spheres[{index}].material.emissionStrength"].value = (sphere.material.emissionStrength)
            self.accumulation_frame = 0

        imgui.pop_id() 

        # Remove button
        remove = imgui.button(f"Remove##{index}")
        imgui.tree_pop()
        return remove

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
        self.imgui.register_texture(self.fbo.color_attachments[0])
        self.imgui.register_texture(self.fbo_prev.color_attachments[0])
        self.imgui.resize(width, height)
        self.accumulation_frame = 0  # Reset accumulation on resize

    def on_key_event(self, key, action, modifiers):

        self.imgui.key_event(key, action, modifiers)

    def on_mouse_position_event(self, x, y, dx, dy):
        self.imgui.mouse_position_event(x, y, dx, dy)

    def on_mouse_drag_event(self, x, y, dx, dy):
        if not imgui.get_io().want_capture_mouse:
            self.accumulation_frame *= not dx and not dy
            self.camera.rotate(dx * self.camera.sensitivity, -dy * self.camera.sensitivity)
        self.imgui.mouse_drag_event(x, y, dx, dy)

    def on_mouse_scroll_event(self, x_offset, y_offset):
        self.imgui.mouse_scroll_event(x_offset, y_offset)

    def on_mouse_press_event(self, x, y, button):
        self.imgui.mouse_press_event(x, y, button)

    def on_mouse_release_event(self, x: int, y: int, button: int):
        self.imgui.mouse_release_event(x, y, button)

    def on_unicode_char_entered(self, char):
        self.imgui.unicode_char_entered(char)


if __name__ == "__main__":
    WindowEvents.run()