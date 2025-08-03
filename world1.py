from dclasses import Sphere, Material
from pyglm.glm import vec3

spheres = [
    Sphere(vec3(-1.73205081, 1.5, -1), 1, Material(emissionColor=vec3(1, .6, .6), emissionStrength=1.6)),
    Sphere(vec3(0,           1.5,  2), 1, Material(emissionColor=vec3(.6, 1, .6), emissionStrength=1.6)),
    Sphere(vec3(1.73205081,  1.5, -1), 1, Material(emissionColor=vec3(.6, .6, 1), emissionStrength=1.6)), 

    Sphere(vec3(0, -400, 0), 400, Material(vec3(1)))
]