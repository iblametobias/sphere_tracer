#version 460

const vec3 quadVertecies[6] = vec3[6](
    vec3(1, -1, 0), 
    vec3(-1, 1, 0), 
    vec3(1, 1, 0), 
    vec3(1, -1, 0), 
    vec3(-1, 1, 0), 
    vec3(-1, -1, 0)
);

void main() {
    vec3 position = quadVertecies[gl_VertexID];
    gl_Position = vec4(position, 1.0);
}