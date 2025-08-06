#version 460
out vec4 fragment;

// RNGs
uint Triple32(inout uint x)
{
    x ^= x >> 17;
    x *= 0xed5ad4bbU;
    x ^= x >> 11;
    x *= 0xac4c1b51U;
    x ^= x >> 15;
    x *= 0x31848babU;
    x ^= x >> 14;
    return x;
}

float Rand(inout uint state) {
    Triple32(state);
    return float(state) * (1.0 / 4294967296.0);
}

float RandGaussian(inout uint state) {
    float u1 = max(Rand(state), 1e-6); // avoid zero
    float u2 = Rand(state);
    float r = sqrt(-2.0 * log(u1));
    float theta = 6.28318530718 * u2; // 2*pi
    return r * cos(theta); // could also return r * sin(theta) if you want pairwise
}

vec3 RandDirection(inout uint state) {
    float x = RandGaussian(state);
    float y = RandGaussian(state);
    float z = RandGaussian(state);
    return normalize(vec3(x, y, z));
}

// Structs
struct Ray {
    vec3 direction;
    vec3 origin;
};

struct Material {
    vec3 color;
    float smoothness;
    vec3 emissionColor;
    float emissionStrength;
};

struct Sphere {
    vec3 center;
    float radius;
    Material material;
};

struct Hit {
    bool happened;
    vec3 position;
    vec3 normal;
    float distance_; 
    Material material;
};



// uniforms and constants
const float PI = 3.141592653589793;

uniform float fov;
uniform vec2 resolution;

uniform float runningTime;

uniform vec3 forward;
uniform vec3 right;
uniform vec3 up;
uniform vec3 position;

uniform sampler2D prev;
uniform int accumulationFrame;

const int MAX_SPHERE_ARRAY_SIZE = 128;
uniform int sphereAmount;
uniform Sphere spheres[MAX_SPHERE_ARRAY_SIZE];

uniform float skyboxLightStrength;
uniform int raysPerPixel;
uniform int maxBounceLimit;
const float rayJitterStrength = 0.002;


Hit RaySphereIntersection(Ray ray, Sphere sphere) {
    Hit hit;
    hit.happened = false;

    vec3 offsetRayOrigin = ray.origin - sphere.center;
    // From the equation: sqrLength(rayOrigin + rayDir * dst) = radius^2
    // Solving for dst results in a quadratic equation with coefficients:

    float a = dot(ray.direction, ray.direction); 
    float b = 2 * dot(offsetRayOrigin, ray.direction);
    float c = dot(offsetRayOrigin, offsetRayOrigin) - sphere.radius * sphere.radius;
    // Quadratic discriminant
    float discriminant = b * b - 4 * a * c; 

    // No solution when d < 0 (ray misses sphere)
    if (discriminant >= 0) {
        // Distance to nearest intersection point (from quadratic formula)
        float dst = (-b - sqrt(discriminant)) / (2 * a);

        // Ignore intersections that occur behind the ray
        if (dst >= 0) {
            hit.happened = true;
            hit.distance_ = dst;
            hit.position = ray.origin + ray.direction * dst;
            hit.normal = normalize(hit.position - sphere.center);
            hit.material = sphere.material;
        }
    }
    return hit;
}


Hit CalculateRayCollision(Ray ray) {
    Hit closestHit;
    closestHit.happened = false;
    closestHit.distance_ = 1e20;
    
    for (int i = 0; i < sphereAmount; i++) {
        Sphere sphere = spheres[i];
        Hit hit = RaySphereIntersection(ray, sphere);
        if (!hit.happened) {
            continue;
        } 
        if (hit.distance_ < closestHit.distance_) {
            closestHit = hit;
        }
    }
    return closestHit;
}

vec3 GetEnvironmentLight(Ray ray) {
    float y = ray.direction.y;
    vec3 color;
    if (y<0) {
        color = vec3(.35);
    } else {

        float bias = min(1, pow(y, 0.5) * 2);
        color = mix(vec3(.8), vec3(.5, .55, .65), bias);
    }
    return color * skyboxLightStrength;
}

vec3 Trace(Ray ray, inout uint rngState) {
    vec3 incomingLight = vec3(0);
    vec3 rayColor = vec3(1);

    for (int i = 0; i <= maxBounceLimit; i++) {
        Hit hit = CalculateRayCollision(ray);
        if (hit.happened) {
            Material material = hit.material;

            vec3 diffuse = normalize(hit.normal + RandDirection(rngState));
            vec3 specular = reflect(ray.direction, hit.normal);
            ray.direction = mix(diffuse, specular, material.smoothness);
            ray.origin = hit.position;

            vec3 emittedLight = material.emissionColor * material.emissionStrength;

            incomingLight += emittedLight * rayColor;
            rayColor *= material.color;

        } else {
            incomingLight += GetEnvironmentLight(ray) * rayColor;
            break;
        }
    }

    return incomingLight;
}

vec3 ACESFilm(vec3 x) {
    const float a = 2.51;
    const float b = 0.03;
    const float c = 2.43;
    const float d = 0.59;
    const float e = 0.14;
    return clamp((x * (a * x + b)) / (x * (c * x + d) + e), 0.0, 1.0);
}


void main() {
    float aspect = resolution.x / resolution.y;
    vec2 uv = gl_FragCoord.xy / resolution;
    vec2 ndc = uv * 2.0 - 1.0; // [-1,1]
    ndc.x *= aspect;
    ndc.y *= -1.0; // Invert y-axis for OpenGL

    float focalLength = 1 / tan(radians(fov) * 0.5);
    vec3 baseRayDirection = vec3(ndc, focalLength);

    mat3 rayScreenToWorld = mat3(right, up, forward);

    uint pixelIndex = uint(gl_FragCoord.y) * uint(resolution.x) + uint(gl_FragCoord.x);
    uint rngState = pixelIndex * 988765 + accumulationFrame * 234567;

    vec3 light = vec3(0);
    for (int i = 0; i < raysPerPixel; i++) {
        vec3 rayJitter = RandDirection(rngState) * rayJitterStrength;
        vec3 rayDirection = normalize(rayJitter + baseRayDirection);
        vec3 rayDirectionWorld = rayScreenToWorld * rayDirection;

        Ray ray = Ray(rayDirectionWorld, position);
        light += Trace(ray, rngState);
    }
    light /= raysPerPixel;

    light = ACESFilm(light);

    vec3 color = mix(texture(prev, uv).rgb, light, 1 / float(accumulationFrame));

    fragment = vec4(color, 1);
}