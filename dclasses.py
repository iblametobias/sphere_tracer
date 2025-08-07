from glm import vec3
from dataclasses import dataclass, field

@dataclass
class Material:
    """
    Represents the Material struct in the shader 
    """
    color: vec3 = field(default_factory=lambda: vec3(0))
    smoothness: float = 0
    emissionColor: vec3 = field(default_factory=lambda: vec3(0))
    emissionStrength: float = 0.0



@dataclass
class Sphere:
    """
    Represents the Sphere struct in the shader 
    """
    center: vec3
    radius: float
    material: Material = field(default_factory=Material())