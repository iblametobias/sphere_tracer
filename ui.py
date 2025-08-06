import imgui
from glm import vec3
from dclasses import Sphere


class UI:
    """
    Handles the only the UI generation
    """
    def __init__(self, app):
        self.app = app

    def generate_frame(self):
        imgui.new_frame()

        # 1. Draw the raytraced frame as a background
        imgui.push_style_var(imgui.STYLE_WINDOW_PADDING, (0, 0))
        imgui.set_next_window_position(0, 0)
        imgui.set_next_window_size(*self.app.window_size)
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
        imgui.image(self.app.fbo.color_attachments[0].glo, *self.app.window_size)
        imgui.end()
        imgui.pop_style_var()

        # --- LEFT SIDEBAR ---
        imgui.set_next_window_position(0, 0)
        imgui.set_next_window_size(self.app.SIDEBAR_WIDTH, self.app.window_size[1])
        imgui.begin(
            "##Sidebar",  # No header/title bar
            False,
            imgui.WINDOW_NO_TITLE_BAR | imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_SAVED_SETTINGS | imgui.WINDOW_NO_MOVE
        )

        # Collapsible Raytracer Settings
        if imgui.collapsing_header("Raytracer Settings", flags=imgui.TREE_NODE_DEFAULT_OPEN)[0]:
            imgui.set_next_item_width(160)
            _, self.app.rays_per_pixel = imgui.slider_int(
                "Rays/Pixel", self.app.rays_per_pixel, 1, 20
            )
            imgui.set_next_item_width(160)
            _, self.app.max_bounce_limit = imgui.slider_int(
                "Max Bounces", self.app.max_bounce_limit, 1, 4
            )
            imgui.text(f"MSPF: {(self.app.delta_time * 1000):.0f} ms")
            imgui.text(f"Accumulation time: {self.app.accumulation_time:.2f}s")
            _, self.app.allow_accumulation = imgui.checkbox(
                "Allow Accumulation", self.app.allow_accumulation
            )

        # Collapsible World Settings
        if imgui.collapsing_header("World Settings", flags=imgui.TREE_NODE_DEFAULT_OPEN)[0]:
            remove_indices = []
            for i, sphere in enumerate(self.app.spheres):
                if self._render_sphere_editor(sphere, i):
                    remove_indices.append(i)

            # Remove spheres after iteration to avoid index issues
            for idx in reversed(remove_indices):
                del self.app.spheres[idx]
                self.app.reset_accumulation()

            if remove_indices:
                self.app.program["sphereAmount"].value = len(self.app.spheres)
                for i, sphere in enumerate(self.app.spheres):
                    self.app.load_dataclass_to_uniform(sphere, f"spheres[{i}]")

        if imgui.button("Add Sphere"):
            from dclasses import Sphere, Material  # Ensure import at top of file
            self.app.spheres.append(Sphere(center=vec3(0,0,0), radius=1.0, material=Material()))
            self.app.reset_accumulation()
            self.app.load_dataclass_to_uniform(self.app.spheres[-1], f"spheres[{len(self.app.spheres) - 1}]")

        if imgui.button("Print all"):
            print(self.app.spheres)

        imgui.end()

        # --- RIGHT SIDEBAR ---
        right_x = self.app.window_size[0] - self.app.SIDEBAR_WIDTH
        imgui.set_next_window_position(right_x, 0)
        imgui.set_next_window_size(self.app.SIDEBAR_WIDTH, self.app.window_size[1])
        imgui.begin(
            "##CameraSidebar",  # No header/title bar
            False,
            imgui.WINDOW_NO_TITLE_BAR | imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_SAVED_SETTINGS | imgui.WINDOW_NO_MOVE
        )

        # Collapsible Camera Controls
        if imgui.collapsing_header("Camera Controls", flags=imgui.TREE_NODE_DEFAULT_OPEN)[0]:
            imgui.text(
                f"Position: ({self.app.camera.position.x:6.2f}, {self.app.camera.position.y:6.2f}, {self.app.camera.position.z:6.2f})"
            )
            imgui.text(
                f"Forward:  ({self.app.camera.forward.x:6.2f}, {self.app.camera.forward.y:6.2f}, {self.app.camera.forward.z:6.2f})"
            )
            imgui.set_next_item_width(160)
            changed, self.app.camera.fov = imgui.slider_float(
                "FOV", self.app.camera.fov, 30.0, 90.0, format="%.0f"
            )
            if changed:
                self.app.reset_accumulation()
            imgui.set_next_item_width(160)
            _, self.app.camera.sensitivity = imgui.slider_float(
                "Sensitivity", self.app.camera.sensitivity, 0.05, 0.4
            )
            imgui.set_next_item_width(100)
            _, self.app.camera.movement_speed = imgui.drag_float(
                "Movement Speed", self.app.camera.movement_speed, 0.02, 0.5, 5.0, format="%.2f"
            )
            _, self.app.camera.allow_sprint = imgui.checkbox(
                "Allow Sprint", self.app.camera.allow_sprint
            )
            imgui.set_next_item_width(100)
            _, self.app.camera.sprint_speed_multiplier = imgui.drag_float(
                "Sprint Speed Multiplier", self.app.camera.sprint_speed_multiplier, 0.05, 2.0, 20.0, format="%.2f"
            )

        imgui.end()
        imgui.render()

    def _render_sphere_editor(self, sphere: Sphere, index: int) -> bool:
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
            self.app.program[f"spheres[{index}].center"].write(sphere.center)
            self.app.reset_accumulation()

        # --- Radius ---
        imgui.set_next_item_width(160)
        radius_changed, sphere.radius = imgui.drag_float(
            f"Radius", sphere.radius, 0.01, 0, 100.0, format="%.2f"
        )
        if radius_changed:
            self.app.program[f"spheres[{index}].radius"].value = sphere.radius
            self.app.reset_accumulation()

        # --- Material ---
        # Color (RGB sliders)
        imgui.set_next_item_width(160)
        color_changed, *new_color = imgui.color_edit3(
            "Albedo", *tuple(sphere.material.color)
        )
        if color_changed:
            sphere.material.color = vec3(*new_color)
            self.app.program[f"spheres[{index}].material.color"].write(sphere.material.color)
            self.app.reset_accumulation()
        # Smoothness
        imgui.set_next_item_width(160)
        changed_smooth, sphere.material.smoothness = imgui.slider_float(
            "Smoothness", sphere.material.smoothness, 0.0, 1.0, format="%.2f"
        )
        if changed_smooth:
            self.app.program[f"spheres[{index}].material.smoothness"].value = (sphere.material.smoothness)
            self.app.reset_accumulation()
        # Emission Color (RGB sliders)
        imgui.set_next_item_width(160)
        emission_changed, *new_emission = imgui.color_edit3(
            "Emission", *tuple(sphere.material.emissionColor)
        )
        if emission_changed:
            sphere.material.emissionColor = vec3(*new_emission)
            self.app.program[f"spheres[{index}].material.emissionColor"].write(sphere.material.emissionColor)
            self.app.reset_accumulation()
        # Emission Strength
        imgui.set_next_item_width(160)
        changed_em_strength, sphere.material.emissionStrength = imgui.drag_float(
            "Brightness", sphere.material.emissionStrength, 0.01, 0, 5, format="%.2f"
        )
        if changed_em_strength:
            self.app.program[f"spheres[{index}].material.emissionStrength"].value = (sphere.material.emissionStrength)
            self.app.reset_accumulation()

        imgui.pop_id() 

        # Remove button
        remove = imgui.button(f"Remove##{index}")
        imgui.tree_pop()
        return remove