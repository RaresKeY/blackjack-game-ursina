#version 330

in vec2 uv;

uniform sampler2D scene_tex;
uniform sampler2D mask_tex;
uniform vec2  screen_size;
uniform float inner_px;        // inner grow in pixels (gap size)
uniform float outer_px;        // outer grow in pixels (halo distance)
uniform vec4  outline_color;

out vec4 fragColor;

// Grow a binary mask by "radius" pixels
float growMask(float radius, vec2 texel) {
    float m = 0.0;
    int r = int(radius);
    for (int x = -r; x <= r; x++) {
        for (int y = -r; y <= r; y++) {
            if (length(vec2(x, y)) > radius) continue;
            vec2 offs = vec2(x, y) * texel;
            
            m = max(m, texture(mask_tex, uv + offs).a);
        }
    }
    return m;
}

void main() {
    vec4 scene = texture(scene_tex, uv);
    vec2 texel = 1.0 / screen_size;

    float inner = growMask(inner_px, texel);
    float outer = growMask(outer_px, texel);

    float ring = clamp(outer - inner, 0.0, 1.0);

    vec3 rgb = mix(scene.rgb, outline_color.rgb, ring * outline_color.a);
    fragColor = vec4(rgb, 1.0);
}
