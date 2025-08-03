#version 460

in vec2 in_vert;

void main() {
    vec3 position = vec3(in_vert, 0.0);
    gl_Position = vec4(position, 1.0);
}